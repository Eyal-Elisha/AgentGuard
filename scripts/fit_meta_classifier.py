"""Fit the meta-classifier (stacking layer) and write the deployable artifact.

This is the script that produces ``backend/analysis/data/meta_classifier.pkl``,
the model that turns the individual rule scores into the single risk value the
proxy acts on. It is deliberately separate from ``train_meta_classifier.py``,
which is a diagnostic bake-off that compares candidate models and writes
nothing.

Inputs
------
A rule-feature JSONL produced by ``scripts/build_rule_features.py``: one record
per page, ``{"label": 0|1, "feat": {rule_id: score, ...}}``. The feature vector
is the score every rule emitted for that page -- the model never sees the page
itself, only what the rules concluded about it. That is what makes this a
*stacking* layer: the rules are level 1, this model is level 2.

Calibration
-----------
The dev split is roughly half phishing; real traffic is not. A model fitted on
it would report ~0.5 for a page it knows nothing about, which is arithmetically
right and useless in a browser. Benign rows are therefore weighted x9 so the
model behaves as though phishing were about a tenth of traffic. This changes
what the number *means*, not which pages outrank which -- ROC AUC is unaffected
by the reweighting.

Reproducibility
---------------
Every step is deterministic: the feature order is sorted alphabetically, the
estimator is seeded, and the weighting is a fixed constant. Re-running this on
the same feature file reproduces the shipped artifact exactly (verify with
--verify-against).

Full pipeline, from the raw dataset to this artifact:

    1. python scripts/load_phreshphish.py --hf-split test --limit 30000 \
           --output data/phreshphish_test_30k.jsonl
    2. python scripts/split_by_domain.py --input data/phreshphish_test_30k.jsonl \
           --dev data/dev.jsonl --test data/test.jsonl
    3. python scripts/build_rule_features.py --input data/dev.jsonl \
           --output runs/dev_feats.jsonl
    4. python scripts/fit_meta_classifier.py --train runs/dev_feats.jsonl \
           --output backend/analysis/data/meta_classifier.pkl

Usage:
    python scripts/fit_meta_classifier.py --train runs/dev_feats.jsonl \
        --output backend/analysis/data/meta_classifier.pkl
    python scripts/fit_meta_classifier.py --train runs/dev_feats.jsonl \
        --eval runs/fresh_feats.jsonl --dry-run \
        --verify-against backend/analysis/data/meta_classifier.pkl
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

# Benign rows are weighted by this factor so the fitted model reports
# probabilities as if phishing were ~10% of traffic rather than ~50%.
BENIGN_WEIGHT = 9.0
TARGET_BASE_RATE = 0.1
RANDOM_STATE = 42


def _load(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
    return [r for r in rows if "feat" in r and r.get("label") in (0, 1)]


def _matrix(rows: list[dict], features: list[str]):
    import numpy as np

    x = np.zeros((len(rows), len(features)), dtype=float)
    y = np.zeros(len(rows), dtype=int)
    for i, rec in enumerate(rows):
        for j, name in enumerate(features):
            x[i, j] = rec["feat"].get(name, 0.0)
        y[i] = rec["label"]
    return x, y


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--train", required=True, type=Path,
                    help="Rule-feature JSONL for the dev split")
    ap.add_argument("--output", type=Path,
                    default=Path("backend/analysis/data/meta_classifier.pkl"))
    ap.add_argument("--eval", type=Path,
                    help="Optional held-out feature JSONL to report metrics on")
    ap.add_argument("--dry-run", action="store_true",
                    help="Fit and report but do not write the artifact")
    ap.add_argument("--verify-against", type=Path,
                    help="Existing artifact; assert the refit reproduces it exactly")
    args = ap.parse_args(argv)

    if not args.train.exists():
        print(f"error: training features not found: {args.train}", file=sys.stderr)
        return 2

    import numpy as np
    from sklearn.ensemble import GradientBoostingClassifier

    rows = _load(args.train)
    if not rows:
        print("error: no usable rows in training file", file=sys.stderr)
        return 2

    # Sorted so the feature order is stable across runs and machines. The
    # artifact stores this list; the runtime builds its vector from it by name,
    # so a rule added later cannot silently shift the columns.
    features = sorted({k for r in rows for k in r["feat"]})
    x, y = _matrix(rows, features)
    weights = np.where(y == 1, 1.0, BENIGN_WEIGHT)

    n_pos, n_neg = int(y.sum()), int((y == 0).sum())
    effective = n_pos / (n_pos + BENIGN_WEIGHT * n_neg)
    print(f"train rows : {len(y)}  ({n_pos} phishing / {n_neg} benign, "
          f"base rate {y.mean():.3f})", file=sys.stderr)
    print(f"features   : {len(features)} -> {features}", file=sys.stderr)
    print(f"weighting  : benign x{BENIGN_WEIGHT} -> effective base rate "
          f"{effective:.3f}", file=sys.stderr)

    model = GradientBoostingClassifier(random_state=RANDOM_STATE)
    model.fit(x, y, sample_weight=weights)

    order = sorted(zip(features, model.feature_importances_), key=lambda kv: -kv[1])
    print("\nfeature importance:", file=sys.stderr)
    for name, importance in order:
        print(f"  {name:<26} {importance:.4f}", file=sys.stderr)

    if args.eval and args.eval.exists():
        from sklearn.metrics import average_precision_score, roc_auc_score

        ev = _load(args.eval)
        xe, ye = _matrix(ev, features)
        se = model.predict_proba(xe)[:, 1]
        print(f"\nheld-out ({args.eval.name}, {len(ye)} rows, "
              f"base rate {ye.mean():.3f}):", file=sys.stderr)
        print(f"  ROC AUC           {roc_auc_score(ye, se):.4f}", file=sys.stderr)
        print(f"  average precision {average_precision_score(ye, se):.4f}", file=sys.stderr)

    if args.verify_against:
        with args.verify_against.open("rb") as fh:
            reference = pickle.load(fh)
        if list(reference["features"]) != features:
            print("\nVERIFY FAILED: feature list differs", file=sys.stderr)
            return 1
        delta = np.abs(model.predict_proba(x)[:, 1]
                       - reference["model"].predict_proba(x)[:, 1]).max()
        print(f"\nverify vs {args.verify_against.name}: "
              f"max |probability difference| = {delta:.3e}", file=sys.stderr)
        if delta > 1e-12:
            print("VERIFY FAILED: refit does not reproduce the artifact", file=sys.stderr)
            return 1
        print("VERIFY OK: refit reproduces the artifact exactly", file=sys.stderr)

    if args.dry_run:
        print("\ndry run: artifact not written", file=sys.stderr)
        return 0

    payload = {
        "model": model,
        "features": features,
        "trained_on": f"{args.train.name} rule-features, "
                      f"reweighted to {TARGET_BASE_RATE} phishing prior",
        "base_rate": TARGET_BASE_RATE,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as fh:
        pickle.dump(payload, fh)
    print(f"\nwrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
