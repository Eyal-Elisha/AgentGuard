"""Stage B, the semantic half: TF-IDF plus logistic regression over the page text.
Runs only when Stage A sets `stage_b_required`.
"""

from backend.analysis.stages.stage_b.evaluator import StageBEvaluator

__all__ = ["StageBEvaluator"]
