"""Turning a set of rule results into one risk score and one decision.

There are two ways to do it, and which one runs depends on whether a trained
artifact is present:

  weighted_average  the hand-calibrated default — every rule's weight is a
                    number someone chose, and the score is their average
  meta_classifier   a model trained on the rule scores themselves, which can
                    read combinations the fixed weights cannot

The weighted average is always available. The meta-classifier is used only
when `analysis/data/meta_classifier.pkl` loads, so a bare install — or a test
run without scikit-learn — falls back to the average and behaves as before.

`proxy/rule_engine.py` is what chooses between them.
"""

from . import meta_classifier
from .weighted_average import aggregate_risk_score, decide

__all__ = ["aggregate_risk_score", "decide", "meta_classifier"]
