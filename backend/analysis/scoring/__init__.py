"""Rule results in, one risk score and one decision out. Two strategies:
weighted_average always works, meta_classifier takes over when its artifact
loads.
"""

from . import meta_classifier
from .floors import apply_decision_floors
from .weighted_average import aggregate_risk_score, decide

__all__ = [
    "aggregate_risk_score",
    "apply_decision_floors",
    "decide",
    "meta_classifier",
]
