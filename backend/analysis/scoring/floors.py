"""Minimum decisions that individual rules can force on their own.

Both scoring strategies reduce every rule to one number and then threshold it,
which means a rule can only ever influence the outcome in proportion to how
much the scorer weighs it. That is the right default and it fails for one case:
a rule that detects a threat class the scorer was never trained to predict.

`DECISION_FLOORS` in `rules.tuning` names those cases. This module applies
them, after scoring, by raising the decision if a listed rule scored at or
above its threshold. It can only ever make a decision stricter.
"""

from __future__ import annotations

import logging
from typing import Iterable, List, Optional, Tuple

from backend.analysis.rules import DECISION_FLOORS, Decision, RuleResult

_logger = logging.getLogger(__name__)

# Ordered least to most restrictive, so a floor is applied by taking the max.
_SEVERITY: dict[Decision, int] = {
    Decision.ALLOW: 0,
    Decision.WARN: 1,
    Decision.BLOCK: 2,
}


def _floor_for(rule_id: str, score: Optional[float]) -> Optional[Decision]:
    policy = DECISION_FLOORS.get(rule_id)
    if not policy or score is None:
        return None
    if float(score) < float(policy["min_score"]):
        return None
    try:
        return Decision(policy["min_decision"])
    except ValueError:  # pragma: no cover - guards a typo in the config
        _logger.warning(
            "decision floor for %s names an unknown decision %r; ignoring",
            rule_id, policy["min_decision"],
        )
        return None


def applicable_floors(
    rule_results: Iterable[RuleResult],
) -> List[Tuple[str, Decision]]:
    """Every (rule_id, minimum decision) a floor rule is currently demanding."""
    out: List[Tuple[str, Decision]] = []
    for result in rule_results:
        if not getattr(result, "triggered", False):
            continue
        floor = _floor_for(result.rule_id, result.score)
        if floor is not None:
            out.append((result.rule_id, floor))
    return out


def apply_decision_floors(
    decision: Decision,
    rule_results: Iterable[RuleResult],
) -> Decision:
    """Raise `decision` to satisfy any rule-specific floor. Never lowers it."""
    floors = applicable_floors(rule_results)
    if not floors:
        return decision
    strictest_id, strictest = max(floors, key=lambda pair: _SEVERITY[pair[1]])
    if _SEVERITY[strictest] <= _SEVERITY[decision]:
        return decision
    _logger.info(
        "decision raised %s -> %s by the %s floor",
        decision.value, strictest.value, strictest_id,
    )
    return strictest
