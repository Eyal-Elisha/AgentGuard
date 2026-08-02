"""Semantic classifier abstraction for Stage B.

Each semantic rule binds to a `model_id`. At runtime we look up a classifier
artifact under `stage_b/data/<model_id>.pkl`. If the artifact exists *and*
scikit-learn is importable, we deserialize it and use `predict_proba`.

If either is missing we fall back to `heuristics.heuristic_score`, which keeps
the pipeline useful before the operator runs
scripts/train_semantic_models.py.

The pickle is expected to contain a scikit-learn `Pipeline` whose final step is
a binary `LogisticRegression`. The positive class label must be `1` (malicious).
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from backend.analysis.stages.stage_b.heuristics import HEURISTIC_MODEL_IDS, heuristic_score

_logger = logging.getLogger(__name__)

_MODEL_DIR = Path(__file__).resolve().parent / "data"
_LOCK = Lock()
_CACHE: Dict[str, "SemanticClassifier"] = {}


class SemanticClassifier:
    """Single binary classifier behind a semantic rule."""

    def __init__(self, model_id: str, model: Optional[Any]) -> None:
        self.model_id = model_id
        self._model = model
        self._using_heuristic = model is None

    @property
    def using_heuristic(self) -> bool:
        return self._using_heuristic

    def predict_proba(self, text: str) -> float:
        """Return probability in [0, 1] that `text` is malicious."""
        if not text:
            return 0.0
        if self._model is None:
            return heuristic_score(self.model_id, text)
        try:
            proba = self._model.predict_proba([text])[0]
            classes = list(getattr(self._model, "classes_", [0, 1]))
            try:
                positive_index = classes.index(1)
            except ValueError:
                positive_index = len(classes) - 1
            return float(proba[positive_index])
        except Exception:
            _logger.exception("Semantic model %s inference failed — using heuristic", self.model_id)
            return heuristic_score(self.model_id, text)


def _artifact_path(model_id: str) -> Path:
    return _MODEL_DIR / f"{model_id}.pkl"


def _try_load(model_id: str) -> Optional[Any]:
    path = _artifact_path(model_id)
    if not path.is_file():
        return None
    try:
        import sklearn  # noqa: F401  (presence check before unpickling)
    except ImportError:
        _logger.info("scikit-learn not installed; semantic rule %s falls back to heuristic", model_id)
        return None
    try:
        with path.open("rb") as fh:
            return pickle.load(fh)
    except Exception:
        _logger.exception("Failed to load semantic model %s from %s", model_id, path)
        return None


def get_classifier(model_id: str) -> SemanticClassifier:
    """Return a cached classifier for `model_id`, building it on first use."""
    cached = _CACHE.get(model_id)
    if cached is not None:
        return cached
    with _LOCK:
        cached = _CACHE.get(model_id)
        if cached is not None:
            return cached
        model = _try_load(model_id)
        classifier = SemanticClassifier(model_id, model)
        _CACHE[model_id] = classifier
        if model is None and model_id not in HEURISTIC_MODEL_IDS:
            _logger.warning("Semantic model %s has neither artifact nor heuristic", model_id)
        return classifier


def clear_cache() -> None:
    """Drop cached classifiers (used by tests after retraining)."""
    with _LOCK:
        _CACHE.clear()
