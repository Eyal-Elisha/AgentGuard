"""Stage B — Expensive Rule Evaluation (Semantic).

Runs only when Stage A flags `stage_b_required` (ambiguous deterministic +
contextual score). Uses TF-IDF + Logistic Regression classifiers — see
`SemanticClassifier`, and scripts/train_semantic_models.py for how the
artifacts in `data/` are produced.
"""

from backend.analysis.stages.stage_b.evaluator import StageBEvaluator

__all__ = ["StageBEvaluator"]
