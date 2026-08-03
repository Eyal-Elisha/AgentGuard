"""A trained model over the rule scores, used instead of the weighted average.

Where `weighted_average` gives every rule a fixed weight and averages, this
takes the whole vector of rule scores as features and returns a learned
probability. It can therefore use *combinations* — a brand mismatch matters far
more when the TLD is also suspicious — which a fixed weighting cannot express.

It is optional. `score()` returns None when no artifact is present and the
caller falls back to the average. That is what happens on a bare install: the
pickle needs scikit-learn, which not every environment has.

The artifact is `analysis/data/meta_classifier.pkl`, holding
`{"model": estimator, "features": [rule_id, ...]}`. `features` is the column
order the model was trained on, so it — not the rule catalogue — decides how
the vector is laid out. The shipped one has fourteen columns: the eleven
deterministic rules that can run (`sensitive_fields` is disabled in code), the
two semantic rules, and a synthetic `_hard_block` flag. The four contextual
rules are absent because they never execute — see `rules/tuning.py`.

`_hard_block` is always 0.0 here, since a hard block returns before the
meta-classifier is consulted. It is in the vector because the training features
came from `scripts/build_rule_features.py`, which scores every page including
the hard-blocked ones.

The artifact ships pre-built and the repo cannot currently regenerate it:
`build_rule_features.py` produces the feature vectors and
`train_meta_classifier.py` runs the bake-off, but neither writes the pickle.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import List, Optional, Sequence

from backend.analysis.rules import (
    META_HIGH_RISK_THRESHOLD,
    META_RAW_BLOCK,
    META_RAW_WARN,
    META_WARN_THRESHOLD,
    Decision,
    RuleResult,
)

_logger = logging.getLogger(__name__)

_ARTIFACT = Path(__file__).resolve().parents[1] / "data" / "meta_classifier.pkl"

_model = None
_feature_order: List[str] = []
_load_attempted = False


def _load() -> None:
    """Read the artifact once. A missing or unreadable one leaves the model
    None, which is the signal to fall back — never an exception."""
    global _model, _feature_order, _load_attempted
    _load_attempted = True
    if not _ARTIFACT.exists():
        return
    try:
        with _ARTIFACT.open("rb") as fh:
            payload = pickle.load(fh)
        _model = payload["model"]
        _feature_order = list(payload["features"])
        _logger.info("meta-classifier loaded (%d features)", len(_feature_order))
    except Exception as exc:
        _logger.warning("meta-classifier failed to load, falling back: %s", exc)
        _model = None
        _feature_order = []


def is_available() -> bool:
    if not _load_attempted:
        _load()
    return _model is not None


# The rescaling described in `rules.tuning`, written as the four points it
# passes through: raw model probability on the left, displayed risk on the
# right. It is linear between any two, which keeps it monotonic — and monotonic
# is the only property that matters here, because it is what guarantees the
# rescaling moves no decision.
_ANCHORS = (
    (0.0, 0.0),
    (META_RAW_WARN, META_WARN_THRESHOLD),
    (META_RAW_BLOCK, META_HIGH_RISK_THRESHOLD),
    (1.0, 1.0),
)


def _to_risk(raw: float) -> float:
    if raw <= 0.0:
        return 0.0
    for (low_raw, low_risk), (high_raw, high_risk) in zip(_ANCHORS, _ANCHORS[1:]):
        if raw <= high_raw:
            span = (raw - low_raw) / (high_raw - low_raw)
            return round(low_risk + span * (high_risk - low_risk), 4)
    return 1.0


def _feature_vector(results: Sequence[RuleResult]) -> List[float]:
    """Rule scores in the order the model was trained on. A rule that did not
    run counts as 0.0, which is how the training features were built too."""
    by_id = {r.rule_id: (float(r.score) if r.score is not None else 0.0) for r in results}
    return [by_id.get(rule_id, 0.0) for rule_id in _feature_order]


def score(results: Sequence[RuleResult]) -> Optional[float]:
    """The model's risk for these rule results, or None if it is unavailable."""
    if not is_available():
        return None
    vector = _feature_vector(results)
    # Nothing fired, so there is no evidence. Short-circuit rather than report
    # the model's small non-zero baseline next to an all-zero rules table,
    # which reads in the dashboard as a score with nothing behind it.
    if not any(vector):
        return 0.0
    return _to_risk(float(_model.predict_proba([vector])[0][1]))


def decide(risk_score: float) -> Decision:
    if risk_score >= META_HIGH_RISK_THRESHOLD:
        return Decision.BLOCK
    if risk_score >= META_WARN_THRESHOLD:
        return Decision.WARN
    return Decision.ALLOW
