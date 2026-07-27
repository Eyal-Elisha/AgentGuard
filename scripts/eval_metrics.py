"""Compute evaluation metrics from a scored JSONL produced by eval_offline.py.

Reads `{url, label, score, decision, hard_block, triggered_rules}` records and
reports:

- Average precision (area under the precision-recall curve)
- ROC AUC
- Precision / recall / F1 at the default Allow/Warn/Block decision (i.e. how
  the running product would behave)
- Precision at recall = 0.9 and FPR at recall = 0.9 (threshold-tuned)
- Confusion matrix at the default decision and at the P@R=0.9 threshold
- Per-rule contribution: how many positives each rule fired on vs how many
  false positives it fired on, plus per-rule lift

If scikit-learn isn't importable we fall back to pure-Python implementations
of average precision and ROC AUC, so this script has no hard dependency.

Usage:
    python scripts/eval_metrics.py --input runs/scores.jsonl
    python scripts/eval_metrics.py --input runs/scores.jsonl --json runs/metrics.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable


def _iter_scored(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _average_precision_py(labels: list[int], scores: list[float]) -> float:
    """Pure-python average precision (area under PR curve).

    Sorts by descending score, walks through, computes precision at each
    positive, averages.
    """
    if not labels:
        return float("nan")
    pos_total = sum(labels)
    if pos_total == 0:
        return float("nan")
    pairs = sorted(zip(scores, labels), key=lambda p: p[0], reverse=True)
    tp = 0
    fp = 0
    ap = 0.0
    last_recall = 0.0
    for _score, label in pairs:
        if label == 1:
            tp += 1
        else:
            fp += 1
        precision = tp / (tp + fp)
        recall = tp / pos_total
        ap += precision * (recall - last_recall)
        last_recall = recall
    return ap


def _roc_auc_py(labels: list[int], scores: list[float]) -> float:
    """Pure-python ROC AUC via Mann-Whitney U on score ranks."""
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    pairs = sorted(zip(scores, labels), key=lambda p: p[0])
    # Assign ranks, averaging ties.
    ranks = [0.0] * len(pairs)
    i = 0
    while i < len(pairs):
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        avg_rank = (i + j) / 2 + 1  # ranks are 1-based
        for k in range(i, j + 1):
            ranks[k] = avg_rank
        i = j + 1
    rank_sum_pos = sum(rank for rank, (_s, lbl) in zip(ranks, pairs) if lbl == 1)
    u = rank_sum_pos - n_pos * (n_pos + 1) / 2
    return u / (n_pos * n_neg)


def _threshold_for_recall(labels: list[int], scores: list[float], target_recall: float) -> tuple[float, float, float]:
    """Lowest threshold that achieves recall >= target_recall.

    Returns (threshold, precision_at_that_threshold, fpr_at_that_threshold).
    Picks the *highest-precision* threshold among those that meet recall.
    """
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0:
        return float("nan"), float("nan"), float("nan")
    pairs = sorted(zip(scores, labels), key=lambda p: p[0], reverse=True)
    tp = 0
    fp = 0
    best = (float("nan"), float("nan"), float("nan"))
    best_precision = -1.0
    for score, label in pairs:
        if label == 1:
            tp += 1
        else:
            fp += 1
        recall = tp / n_pos
        precision = tp / (tp + fp)
        fpr = fp / n_neg if n_neg else 0.0
        if recall >= target_recall and precision > best_precision:
            best_precision = precision
            best = (score, precision, fpr)
    return best


def _decide(score: float, warn_threshold: float, block_threshold: float) -> str:
    if score >= block_threshold:
        return "block"
    if score >= warn_threshold:
        return "warn"
    return "allow"


def _confusion(labels: list[int], preds: list[int]) -> dict:
    tp = sum(1 for y, p in zip(labels, preds) if y == 1 and p == 1)
    fp = sum(1 for y, p in zip(labels, preds) if y == 0 and p == 1)
    tn = sum(1 for y, p in zip(labels, preds) if y == 0 and p == 0)
    fn = sum(1 for y, p in zip(labels, preds) if y == 1 and p == 0)
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else float("nan")
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def _rule_breakdown(records: list[dict]) -> dict:
    """For each rule, count fires on positives vs negatives + lift."""
    fires_pos: dict[str, int] = defaultdict(int)
    fires_neg: dict[str, int] = defaultdict(int)
    n_pos = sum(1 for r in records if r.get("label") == 1)
    n_neg = sum(1 for r in records if r.get("label") == 0)
    seen_rules: set[str] = set()
    for r in records:
        label = r.get("label")
        for tr in r.get("triggered_rules", []) or []:
            rid = tr.get("rule_id")
            if not rid:
                continue
            seen_rules.add(rid)
            if label == 1:
                fires_pos[rid] += 1
            elif label == 0:
                fires_neg[rid] += 1
    breakdown = {}
    for rid in sorted(seen_rules):
        tpr = fires_pos[rid] / n_pos if n_pos else float("nan")
        fpr = fires_neg[rid] / n_neg if n_neg else float("nan")
        lift = (tpr / fpr) if fpr and not math.isnan(fpr) and fpr > 0 else float("inf")
        breakdown[rid] = {
            "fires_on_phish": fires_pos[rid],
            "fires_on_benign": fires_neg[rid],
            "tpr": tpr,
            "fpr": fpr,
            "lift": lift,
        }
    return breakdown


_SCORE_BINS: tuple[tuple[str, float, float], ...] = (
    ("== 0",        0.0,  0.0),
    ("(0, 0.10)",   0.0,  0.10),
    ("[0.10, 0.25)", 0.10, 0.25),
    ("[0.25, 0.50)", 0.25, 0.50),
    ("[0.50, 0.70)", 0.50, 0.70),
    ("[0.70, 1.0]",  0.70, 1.01),
)


def _score_histogram(labeled: list[dict]) -> dict:
    """Count scores per bin, split by label, to show where phish/benign land."""
    out: dict[str, dict[str, int]] = {}
    for name, lo, hi in _SCORE_BINS:
        phish = benign = 0
        for r in labeled:
            s = float(r["score"])
            in_bin = (s == 0.0) if (lo == 0.0 and hi == 0.0) else (lo <= s < hi)
            if not in_bin:
                continue
            if r["label"] == 1:
                phish += 1
            else:
                benign += 1
        out[name] = {"phish": phish, "benign": benign}
    return out


def _decision_breakdown(labeled: list[dict], decisions: list[str]) -> dict:
    """allow/warn/block counts overall and split by label."""
    overall: dict[str, int] = defaultdict(int)
    phish: dict[str, int] = defaultdict(int)
    benign: dict[str, int] = defaultdict(int)
    for r, d in zip(labeled, decisions):
        overall[d] += 1
        (phish if r["label"] == 1 else benign)[d] += 1
    keys = ("allow", "warn", "block")
    return {
        "overall": {k: overall.get(k, 0) for k in keys},
        "phish": {k: phish.get(k, 0) for k in keys},
        "benign": {k: benign.get(k, 0) for k in keys},
    }


def compute(
    records: list[dict],
    *,
    warn_threshold: float | None = None,
    block_threshold: float | None = None,
) -> dict:
    labeled = [r for r in records if r.get("label") in (0, 1) and isinstance(r.get("score"), (int, float))]
    skipped = len(records) - len(labeled)
    if not labeled:
        return {"error": "no labeled records with numeric scores", "n_input": len(records)}

    labels = [int(r["label"]) for r in labeled]
    scores = [float(r["score"]) for r in labeled]

    # Effective decision: recompute from score when thresholds are overridden
    # (so a single scored run can be re-judged at any threshold), otherwise
    # trust the decision the harness already wrote.
    override = warn_threshold is not None and block_threshold is not None
    if override:
        decisions = [
            "block" if r.get("hard_block") else _decide(float(r["score"]), warn_threshold, block_threshold)
            for r in labeled
        ]
    else:
        decisions = [str(r.get("decision", "")) for r in labeled]

    # "Default" decision = the product's actual behavior: Warn or Block both count as positive.
    preds_default = [1 if d in ("warn", "block") else 0 for d in decisions]
    preds_block_only = [1 if d == "block" else 0 for d in decisions]

    ap = _average_precision_py(labels, scores)
    auc = _roc_auc_py(labels, scores)
    thr_r09, p_at_r09, fpr_at_r09 = _threshold_for_recall(labels, scores, 0.9)
    preds_r09 = [1 if s >= thr_r09 else 0 for s in scores] if not math.isnan(thr_r09) else None

    n_pos = sum(labels)
    n_neg = len(labels) - n_pos

    stage_b_flags = [r.get("stage_b_ran") for r in labeled if "stage_b_ran" in r]
    stage_b_ran_rate = (sum(1 for f in stage_b_flags if f) / len(stage_b_flags)) if stage_b_flags else None

    return {
        "n_input": len(records),
        "n_skipped": skipped,
        "n_scored": len(labeled),
        "n_positives": n_pos,
        "n_negatives": n_neg,
        "base_rate": n_pos / len(labeled),
        "thresholds": {
            "warn": warn_threshold,
            "block": block_threshold,
            "source": "override" if override else "as-scored",
        },
        "average_precision": ap,
        "roc_auc": auc,
        "precision_at_recall_0.9": p_at_r09,
        "fpr_at_recall_0.9": fpr_at_r09,
        "threshold_at_recall_0.9": thr_r09,
        "stage_b_ran_rate": stage_b_ran_rate,
        "decision_breakdown": _decision_breakdown(labeled, decisions),
        "score_histogram": _score_histogram(labeled),
        "default_decision_warn_or_block": _confusion(labels, preds_default),
        "default_decision_block_only": _confusion(labels, preds_block_only),
        "tuned_threshold_at_recall_0.9": _confusion(labels, preds_r09) if preds_r09 else None,
        "per_rule": _rule_breakdown(labeled),
    }


def _print_report(m: dict, *, stream=sys.stdout) -> None:
    def w(s: str = "") -> None:
        print(s, file=stream)

    if "error" in m:
        w(f"error: {m['error']}")
        return
    w("=" * 60)
    w("AgentGuard offline evaluation")
    w("=" * 60)
    w(f"records in:       {m['n_input']}")
    w(f"  scored:         {m['n_scored']}")
    w(f"  skipped:        {m['n_skipped']}")
    w(f"  positives:      {m['n_positives']}")
    w(f"  negatives:      {m['n_negatives']}")
    w(f"  base rate:      {m['base_rate']:.4f}")
    sb = m.get("stage_b_ran_rate")
    if sb is not None:
        w(f"  stage B ran on: {sb:.1%} of scored pages")
    th = m.get("thresholds", {})
    if th.get("source") == "override":
        w(f"  thresholds:     warn>={th['warn']}  block>={th['block']} (override)")
    w()
    w("score-based metrics (threshold-free)")
    w(f"  average precision : {m['average_precision']:.4f}")
    w(f"  ROC AUC           : {m['roc_auc']:.4f}")
    w()

    hist = m.get("score_histogram")
    if hist:
        w("score distribution (phish / benign)")
        for name, counts in hist.items():
            w(f"  {name:<14} {counts['phish']:>7} / {counts['benign']}")
        w()

    dec = m.get("decision_breakdown")
    if dec:
        w("decision breakdown (allow / warn / block)")
        for grp in ("overall", "phish", "benign"):
            d = dec[grp]
            w(f"  {grp:<8} allow={d['allow']:<7} warn={d['warn']:<7} block={d['block']}")
        w()

    w(f"precision @ recall=0.9 : {m['precision_at_recall_0.9']:.4f}")
    w(f"FPR        @ recall=0.9 : {m['fpr_at_recall_0.9']:.4f}")
    w(f"threshold  @ recall=0.9 : {m['threshold_at_recall_0.9']:.4f}")
    w()
    for name, key in [
        ("Decision = Warn or Block", "default_decision_warn_or_block"),
        ("Decision = Block only",    "default_decision_block_only"),
        ("Tuned threshold @ R=0.9",  "tuned_threshold_at_recall_0.9"),
    ]:
        d = m.get(key)
        if not d:
            continue
        w(f"{name}")
        w(f"  TP={d['tp']:<6} FP={d['fp']:<6} TN={d['tn']:<6} FN={d['fn']}")
        w(f"  precision={d['precision']:.4f}  recall={d['recall']:.4f}  f1={d['f1']:.4f}")
        w()

    w("per-rule contribution (sorted by lift)")
    w(f"  {'rule_id':<32} {'TPR':>8} {'FPR':>8} {'lift':>8}  phish/benign fires")
    rows = sorted(m["per_rule"].items(), key=lambda kv: (-kv[1]["lift"] if kv[1]["lift"] != float("inf") else -1e18, -kv[1]["tpr"]))
    for rid, r in rows:
        lift = "inf" if r["lift"] == float("inf") else f"{r['lift']:.2f}"
        w(f"  {rid:<32} {r['tpr']:>8.3f} {r['fpr']:>8.3f} {lift:>8}  {r['fires_on_phish']} / {r['fires_on_benign']}")
    w()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Scored JSONL from eval_offline.py")
    parser.add_argument("--json", type=Path, help="Also write metrics as JSON")
    parser.add_argument(
        "--warn-threshold",
        type=float,
        default=None,
        help="Re-judge decisions at this warn cutoff from the stored score "
        "(use together with --block-threshold; otherwise the as-scored decisions are used).",
    )
    parser.add_argument(
        "--block-threshold",
        type=float,
        default=None,
        help="Re-judge decisions at this block cutoff from the stored score.",
    )
    args = parser.parse_args(argv)

    if (args.warn_threshold is None) != (args.block_threshold is None):
        print("error: pass both --warn-threshold and --block-threshold, or neither", file=sys.stderr)
        return 2

    if not args.input.exists():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2

    records = list(_iter_scored(args.input))
    metrics = compute(
        records,
        warn_threshold=args.warn_threshold,
        block_threshold=args.block_threshold,
    )
    _print_report(metrics)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with args.json.open("w", encoding="utf-8") as out:
            json.dump(metrics, out, indent=2, default=lambda o: None if isinstance(o, float) and math.isnan(o) else o)
        print(f"wrote {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
