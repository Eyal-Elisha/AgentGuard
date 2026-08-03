"""Turning a set of rule results into one risk score and one decision.

Two strategies, picked by `proxy/rule_engine.py`:

  weighted_average  the hand-calibrated default, always available
  meta_classifier   a model over the rule scores, used when its artifact loads

Without the artifact (a bare install, or tests without scikit-learn) the
average takes over and behaves as it always did.
"""

from . import meta_classifier
from .weighted_average import aggregate_risk_score, decide

__all__ = ["aggregate_risk_score", "decide", "meta_classifier"]
