"""Force semantic classifiers into heuristic mode for Stage B unit tests.

The unit tests assert against the deterministic keyword-bag scorer so they
behave the same whether or not the operator has trained the real classifiers.
End-to-end behaviour against the trained pickles is exercised manually via the
smoke-test in the project README / training docs.
"""

import pytest

from backend.analysis.stages.stage_b import classifier as classifier_module


@pytest.fixture(autouse=True)
def _force_heuristic_mode(monkeypatch):
    monkeypatch.setattr(classifier_module, "_try_load", lambda model_id: None)
    classifier_module.clear_cache()
    yield
    classifier_module.clear_cache()
