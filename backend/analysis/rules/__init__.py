"""Rule definitions: the types, the calibration, and the catalogue.

  models   the types a rule and its result are expressed in
  tuning   every calibrated number — thresholds, weights, per-rule config
  catalog  the sixteen rules themselves

The rest of the codebase imports from `backend.analysis.rules` directly; the
split is for reading, not for addressing.
"""

from .catalog import (
    ALL_RULES,
    CONTEXTUAL_RULES,
    DETERMINISTIC_RULES,
    RULES_BY_ID,
    SEMANTIC_RULES,
)
from .models import (
    ComputeClass,
    Decision,
    EvaluationResult,
    PriorEvent,
    RuleDefinition,
    RuleResult,
    RuleType,
    SessionContext,
)
from .tuning import (
    AMBIGUOUS_LOW,
    CODE_DISABLED_RULES,
    CONTEXTUAL_RULE_CONFIG,
    HIGH_RISK_THRESHOLD,
    RULE_WEIGHTS,
    SEMANTIC_RULE_CONFIG,
    STAGE_B_HIGH,
    STAGE_B_LOW,
    WARN_THRESHOLD,
    is_rule_enabled,
)

__all__ = [
    "ALL_RULES",
    "AMBIGUOUS_LOW",
    "CODE_DISABLED_RULES",
    "CONTEXTUAL_RULES",
    "CONTEXTUAL_RULE_CONFIG",
    "ComputeClass",
    "DETERMINISTIC_RULES",
    "Decision",
    "EvaluationResult",
    "HIGH_RISK_THRESHOLD",
    "PriorEvent",
    "RULES_BY_ID",
    "RULE_WEIGHTS",
    "RuleDefinition",
    "RuleResult",
    "RuleType",
    "SEMANTIC_RULES",
    "SEMANTIC_RULE_CONFIG",
    "STAGE_B_HIGH",
    "STAGE_B_LOW",
    "SessionContext",
    "WARN_THRESHOLD",
    "is_rule_enabled",
]
