"""Optional trained meta-classifier over rule outputs (stacking layer).

If the artifact ``analysis/data/meta_classifier.pkl`` is present, it replaces the
hand-weighted-average aggregation in the live proxy path: it takes the score of
every rule as a feature vector and returns a learned phishing probability. This
captures non-linear signal *combinations* the fixed weighted mean cannot, which
sharply lowers the false-positive rate at realistic base rates.

When the artifact is absent, ``score`` returns ``None`` and callers fall back to
the weighted average — so tests and environments without the model are
unaffected.

The artifact is a dict: {"model": sklearn estimator, "features": [rule_id, ...]}.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import List, Optional

from backend.analysis.rules import RuleResult

_logger = logging.getLogger(__name__)
_ARTIFACT = Path(__file__).resolve().parent / "data" / "meta_classifier.pkl"

_loaded = False
_model = None
_features: List[str] = []


def _load() -> None:
    global _loaded, _model, _features
    _loaded = True
    if not _ARTIFACT.exists():
        return
    try:
        with _ARTIFACT.open("rb") as fh:
            payload = pickle.load(fh)
        _model = payload["model"]
        _features = list(payload["features"])
        _logger.info("meta-classifier loaded (%d features)", len(_features))
    except Exception as exc:  # pragma: no cover - defensive
        _logger.warning("meta-classifier failed to load, falling back: %s", exc)
        _model = None
        _features = []


def is_available() -> bool:
    if not _loaded:
        _load()
    return _model is not None


def score(rule_results: List[RuleResult]) -> Optional[float]:
    """Return the meta-classifier's phishing probability for these rule results,
    or ``None`` if no model artifact is available (caller should fall back)."""
    if not is_available():
        return None
    by_id = {r.rule_id: (float(r.score) if r.score is not None else 0.0)
             for r in rule_results}
    vector = [[by_id.get(name, 0.0) for name in _features]]
    prob = _model.predict_proba(vector)[0][1]
    return float(prob)
