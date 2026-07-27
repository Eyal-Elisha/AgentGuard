"""Recommend warn/block thresholds from a scored DEV split.

Reads a scored JSONL produced by ``eval_offline.py`` (one ``{label, score}``
per line) and sweeps every distinct score to recommend two cutoffs:

* ``warn``  — the lowest score that still reaches a target *recall* (catch as
  many phishing pages as possible while staying as precise as the data allows).
* ``block`` — the lowest score that reaches a target *precision* (only auto-block
  when we are confident, to keep benign false-blocks rare).

Feed the recommended numbers back into the harness without changing product
code:

    python scripts/eval_offline.py --input data/test.jsonl --output runs/test.jsonl \
        --warn-threshold 0.12 --block-threshold 0.55
    python scripts/eval_metrics.py --input runs/test.jsonl \
        --warn-threshold 0.12 --block-threshold 0.55

IMPORTANT: calibrate on a *dev* split and report on a *separate* test split.
Tuning thresholds on the same rows you later quote numbers from is leakage.

Usage:
    python scripts/calibrate_thresholds.py --input runs/dev_scored.jsonl
    python scripts/calibrate_thresholds.py --input runs/dev_scored.jsonl \
        --target-recall 0.9 --target-precision 0.9 --json runs/thresholds.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable


def _iter_scored(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _sweep(labels: list[int], scores: list[float]) -> list[dict]:
    """Precision / recall / FPR at every distinct score, treated as 'flag if >= t'."""
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return []

    pairs = sorted(zip(scores, labels), key=lambda p: p[0], reverse=True)
    points: list[dict] = []
    tp = fp = 0
    i = 0
    while i < len(pairs):
        score = pairs[i][0]
        # Consume all rows sharing this score so the threshold is well-defined.
        while i < len(pairs) and pairs[i][0] == score:
            if pairs[i][1] == 1:
                tp += 1
            else:
                fp += 1
            i += 1
        points.append({
            "threshold": score,
            "precision": tp / (tp + fp) if (tp + fp) else 0.0,
            "recall": tp / n_pos,
            "fpr": fp / n_neg,
        })
    return points


def _lowest_threshold_for_recall(points: list[dict], target: float) -> dict | None:
    """Lowest threshold reaching the recall target, best precision among ties."""
    candidates = [p for p in points if p["recall"] >= target]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p["precision"], p["threshold"]))


def _lowest_threshold_for_precision(points: list[dict], target: float) -> dict | None:
    """Lowest threshold reaching the precision target, best recall among ties."""
    candidates = [p for p in points if p["precision"] >= target]
    if not candidates:
        return None
    return min(candidates, key=lambda p: p["threshold"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path, help="Scored JSONL (dev split)")
    parser.add_argument("--target-recall", type=float, default=0.90, help="Recall target for the warn cutoff")
    parser.add_argument("--target-precision", type=float, default=0.90, help="Precision target for the block cutoff")
    parser.add_argument("--json", type=Path, help="Also write the recommendation as JSON")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2

    records = [r for r in _iter_scored(args.input)
               if r.get("label") in (0, 1) and isinstance(r.get("score"), (int, float))]
    if not records:
        print("error: no labeled records with numeric scores", file=sys.stderr)
        return 2

    labels = [int(r["label"]) for r in records]
    scores = [float(r["score"]) for r in records]
    points = _sweep(labels, scores)
    if not points:
        print("error: need both phishing and benign labels to calibrate", file=sys.stderr)
        return 2

    warn = _lowest_threshold_for_recall(points, args.target_recall)
    block = _lowest_threshold_for_precision(points, args.target_precision)

    print("=" * 60)
    print("AgentGuard threshold calibration (dev split)")
    print("=" * 60)
    print(f"rows: {len(records)}  phish: {sum(labels)}  benign: {len(labels) - sum(labels)}")
    print()

    if warn:
        print(f"warn  -> {warn['threshold']:.4f}  "
              f"(recall={warn['recall']:.3f} precision={warn['precision']:.3f} fpr={warn['fpr']:.3f}) "
              f"[target recall >= {args.target_recall}]")
    else:
        print(f"warn  -> no threshold reaches recall >= {args.target_recall}")
    if block:
        print(f"block -> {block['threshold']:.4f}  "
              f"(recall={block['recall']:.3f} precision={block['precision']:.3f} fpr={block['fpr']:.3f}) "
              f"[target precision >= {args.target_precision}]")
    else:
        print(f"block -> no threshold reaches precision >= {args.target_precision}")
    print()
    print("apply with:")
    w = f"{warn['threshold']:.4f}" if warn else "<none>"
    b = f"{block['threshold']:.4f}" if block else "<none>"
    print(f"  --warn-threshold {w} --block-threshold {b}")
    print()
    print("note: calibrate on dev, report on a separate test split.")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with args.json.open("w", encoding="utf-8") as out:
            json.dump({
                "n_rows": len(records),
                "target_recall": args.target_recall,
                "target_precision": args.target_precision,
                "warn": warn,
                "block": block,
            }, out, indent=2)
        print(f"wrote {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
