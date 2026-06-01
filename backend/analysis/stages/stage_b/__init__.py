"""Stage B — Expensive Rule Evaluation (Semantic).

Runs only when Stage A flags `stage_b_required` (ambiguous deterministic +
contextual score). Uses TF-IDF + Logistic Regression classifiers — see
`SemanticClassifier` and the `train.py` script for model lifecycle.
"""

from backend.analysis.stages.stage_b.evaluator import StageBEvaluator

__all__ = ["StageBEvaluator"]
