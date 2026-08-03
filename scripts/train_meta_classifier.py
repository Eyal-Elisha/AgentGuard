"""Bake-off: trained meta-classifier over rule outputs vs the hand-weighted mean.

Trains on dev rule-feature vectors, evaluates on a held-out set, and prints a
head-to-head at realistic phishing base rates. Purely diagnostic — does not
touch product code. Adopt the meta-classifier only if it clearly wins.

Usage:
    python scripts/train_meta_classifier.py --train runs/dev_feats.jsonl \
        --test runs/fresh_feats.jsonl --baseline runs/fresh_softhttp.jsonl
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path


def _load(path: Path):
    rows = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]
    return [r for r in rows if "feat" in r and r.get("label") in (0, 1)]


def _matrix(rows, keys):
    import numpy as np
    X = np.zeros((len(rows), len(keys)), dtype=float)
    y = np.zeros(len(rows), dtype=int)
    for i, r in enumerate(rows):
        for j, k in enumerate(keys):
            X[i, j] = r["feat"].get(k, 0.0)
        y[i] = r["label"]
    return X, y


def _prec_at_base(y, scores, base_rates, recalls_wanted):
    """For each wanted recall, find the threshold, then report FPR and precision
    at each base rate."""
    import numpy as np
    order = np.argsort(-scores)
    y_sorted = y[order]
    P = y.sum(); N = len(y) - P
    tp = np.cumsum(y_sorted); fp = np.cumsum(1 - y_sorted)
    recall = tp / P; fpr = fp / N
    out = []
    for rw in recalls_wanted:
        idx = np.searchsorted(recall, rw)
        idx = min(idx, len(recall) - 1)
        r = recall[idx]; f = fpr[idx]
        precs = {br: (br * r) / (br * r + (1 - br) * f) if (br * r + (1 - br) * f) else 0.0
                 for br in base_rates}
        out.append((rw, r, f, precs))
    return out


def _ap_auc(y, scores):
    from sklearn.metrics import average_precision_score, roc_auc_score
    return average_precision_score(y, scores), roc_auc_score(y, scores)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train", required=True, type=Path)
    ap.add_argument("--test", required=True, type=Path)
    ap.add_argument("--baseline", type=Path, help="Weighted-average scored JSONL for the same test rows")
    args = ap.parse_args(argv)

    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingClassifier

    tr = _load(args.train); te = _load(args.test)
    keys = sorted({k for r in tr for k in r["feat"]})
    print(f"train={len(tr)}  test={len(te)}  features={len(keys)}: {keys}\n", file=sys.stderr)
    Xtr, ytr = _matrix(tr, keys); Xte, yte = _matrix(te, keys)

    base_rates = [0.50, 0.05, 0.01]
    recalls = [0.30, 0.50, 0.70]

    models = {
        "LogisticRegression": LogisticRegression(class_weight="balanced", max_iter=2000, C=1.0),
        "GradientBoosting": GradientBoostingClassifier(random_state=42),
    }
    results = {}
    for name, m in models.items():
        m.fit(Xtr, ytr)
        s = m.predict_proba(Xte)[:, 1]
        results[name] = s
        apv, aucv = _ap_auc(yte, s)
        print(f"=== {name} ===  AP={apv:.3f}  AUC={aucv:.3f}")
        for rw, r, f, precs in _prec_at_base(yte, s, base_rates, recalls):
            print(f"  recall {r:.2f}: FPR={f:.4f}  prec@50%={precs[0.5]:.3f}  prec@5%={precs[0.05]:.3f}  prec@1%={precs[0.01]:.3f}")
        # feature importance for LR
        if name == "LogisticRegression":
            coef = m.coef_[0]
            imp = sorted(zip(keys, coef), key=lambda kv: -abs(kv[1]))
            print("  top weights:", [(k, round(v, 2)) for k, v in imp[:8]])
        print()

    # Baseline (weighted average) on the same rows
    if args.baseline and args.baseline.exists():
        base = {}
        # align by nothing available; use the baseline file's own label+score distribution
        by = []; bs = []
        for l in args.baseline.open(encoding="utf-8"):
            r = json.loads(l)
            if r.get("label") in (0, 1) and isinstance(r.get("score"), (int, float)):
                by.append(r["label"]); bs.append(r["score"])
        by = np.array(by); bs = np.array(bs)
        apv, aucv = _ap_auc(by, bs)
        print(f"=== BASELINE weighted-average ===  AP={apv:.3f}  AUC={aucv:.3f}")
        for rw, r, f, precs in _prec_at_base(by, bs, base_rates, recalls):
            print(f"  recall {r:.2f}: FPR={f:.4f}  prec@50%={precs[0.5]:.3f}  prec@5%={precs[0.05]:.3f}  prec@1%={precs[0.01]:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
