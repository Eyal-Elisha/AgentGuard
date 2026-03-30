"""Rule definitions — classes, enums, registry, and scoring configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class RuleType(str, Enum):
    DETERMINISTIC = "deterministic"
    CONTEXTUAL = "contextual"
    SEMANTIC = "semantic"


class ComputeClass(str, Enum):
    CHEAP = "cheap"
    EXPENSIVE = "expensive"


class Decision(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


# ---------------------------------------------------------------------------
# Core data classes
# ---------------------------------------------------------------------------

@dataclass
class RuleDefinition:
    """Static metadata describing a single rule."""
    rule_id: str
    description: str
    rule_type: RuleType
    compute_class: ComputeClass
    weight: float
    hard_block: bool


@dataclass
class RuleResult:
    """Output produced after evaluating one rule against a request."""
    rule_id: str
    rule_type: RuleType
    score: Optional[float]   # None → skipped (recorded as NULL per spec)
    hard_block: bool
    explanation: str
    triggered: bool


@dataclass
class EvaluationResult:
    """Final output of any rule engine stage or the full pipeline."""
    decision: Decision
    risk_score: float
    rule_results: List[RuleResult]
    hard_block_triggered: bool = False
    stage_b_required: bool = False


@dataclass
class SessionContext:
    """Snapshot of prior high-impact actions in the current session."""
    previous_urls: List[str] = field(default_factory=list)
    sensitive_interaction_count: int = 0
    unique_domains_visited: int = 0


# ---------------------------------------------------------------------------
# Scoring thresholds (to be calibrated during model evaluation phase)
# ---------------------------------------------------------------------------

HIGH_RISK_THRESHOLD: float = 0.70   # Score above this → BLOCK
WARN_THRESHOLD: float = 0.40        # Score above this (and below HIGH) → WARN
AMBIGUOUS_LOW: float = 0.25         # Deterministic score below this → skip contextual rules
STAGE_B_LOW: float = WARN_THRESHOLD
STAGE_B_HIGH: float = HIGH_RISK_THRESHOLD

# ---------------------------------------------------------------------------
# Rule weights (placeholder — to be calibrated)
# ---------------------------------------------------------------------------

RULE_WEIGHTS: Dict[str, float] = {
    "domain_blacklist":       0.25,
    "unencrypted_connection": 0.20,
    "sensitive_fields":       0.20,
    "brand_domain_mismatch":  0.15,
    "unexpected_redirect":    0.10,
    "external_form_action":   0.10,
    "typosquatting":          0.25,
    "ip_based_url":           0.05,
    "custom_blacklist":       0.25,
}

# ---------------------------------------------------------------------------
# Deterministic rule registry
# ---------------------------------------------------------------------------

DETERMINISTIC_RULES: List[RuleDefinition] = [
    RuleDefinition(
        "domain_blacklist",
        "Domain in Popular Blacklist",
        RuleType.DETERMINISTIC, ComputeClass.CHEAP,
        RULE_WEIGHTS["domain_blacklist"], hard_block=True,
    ),
    RuleDefinition(
        "unencrypted_connection",
        "Unencrypted or Invalid Secure Connection",
        RuleType.DETERMINISTIC, ComputeClass.CHEAP,
        RULE_WEIGHTS["unencrypted_connection"], hard_block=True,
    ),
    RuleDefinition(
        "sensitive_fields",
        "Sensitive Fields Present",
        RuleType.DETERMINISTIC, ComputeClass.CHEAP,
        RULE_WEIGHTS["sensitive_fields"], hard_block=False,
    ),
    RuleDefinition(
        "brand_domain_mismatch",
        "Brand Domain Mismatch",
        RuleType.DETERMINISTIC, ComputeClass.CHEAP,
        RULE_WEIGHTS["brand_domain_mismatch"], hard_block=False,
    ),
    RuleDefinition(
        "unexpected_redirect",
        "Unexpected Redirect During Sensitive Interaction",
        RuleType.DETERMINISTIC, ComputeClass.CHEAP,
        RULE_WEIGHTS["unexpected_redirect"], hard_block=False,
    ),
    RuleDefinition(
        "external_form_action",
        "External Form Action",
        RuleType.DETERMINISTIC, ComputeClass.CHEAP,
        RULE_WEIGHTS["external_form_action"], hard_block=False,
    ),
    RuleDefinition(
        "typosquatting",
        "Typosquatting Domain Detection",
        RuleType.DETERMINISTIC, ComputeClass.CHEAP,
        RULE_WEIGHTS["typosquatting"], hard_block=True,
    ),
    RuleDefinition(
        "ip_based_url",
        "IP Based URL Usage",
        RuleType.DETERMINISTIC, ComputeClass.CHEAP,
        RULE_WEIGHTS["ip_based_url"], hard_block=False,
    ),
    RuleDefinition(
        "custom_blacklist",
        "Custom Local Blacklist",
        RuleType.DETERMINISTIC, ComputeClass.CHEAP,
        RULE_WEIGHTS["custom_blacklist"], hard_block=True,
    ),
]
