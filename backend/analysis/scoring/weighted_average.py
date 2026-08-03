"""Rule results in, one risk score and one decision out. Used by Stage A on its
own rules, then again over both stages once Stage B has run.
"""

from __future__ import annotations

from typing import Iterable

from backend.analysis.rules import (
    HIGH_RISK_THRESHOLD,
    RULE_WEIGHTS,
    WARN_THRESHOLD,
    Decision,
    RuleResult,
)


def aggregate_risk_score(results: Iterable[RuleResult]) -> float:
    """Weighted average over the rules that actually ran.

    Skipped rules (score None) are left out rather than counted as zero, so a
    rule whose preconditions were not met cannot dilute the score.
    """
    weighted_sum = 0.0
    total_weight = 0.0
    for result in results:
        if result.score is None:
            continue
        weight = RULE_WEIGHTS.get(result.rule_id, 0.0)
        weighted_sum += result.score * weight
        total_weight += weight
    return weighted_sum / total_weight if total_weight > 0 else 0.0


def decide(risk_score: float) -> Decision:
    if risk_score >= HIGH_RISK_THRESHOLD:
        return Decision.BLOCK
    if risk_score >= WARN_THRESHOLD:
        return Decision.WARN
    return Decision.ALLOW
