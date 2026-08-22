"""Rule definitions, split for reading: models (the types), tuning (the calibrated
numbers), catalog (the eighteen rules). Everything imports from
`backend.analysis.rules` directly.
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
    DECISION_FLOORS,
    HIGH_RISK_THRESHOLD,
    META_HIGH_RISK_THRESHOLD,
    META_RAW_BLOCK,
    META_RAW_WARN,
    META_WARN_THRESHOLD,
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
    "DECISION_FLOORS",
    "DETERMINISTIC_RULES",
    "Decision",
    "EvaluationResult",
    "HIGH_RISK_THRESHOLD",
    "META_HIGH_RISK_THRESHOLD",
    "META_RAW_BLOCK",
    "META_RAW_WARN",
    "META_WARN_THRESHOLD",
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
