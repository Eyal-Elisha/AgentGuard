"""Rule definitions — classes, enums, registry, and scoring configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


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
class PriorEvent:
    """Lightweight snapshot of a single prior event in the current session.

    Built by the session loader from the `events` table; consumed by contextual
    rules. Kept intentionally minimal so the analysis layer does not depend on
    the full storage row shape.
    """
    timestamp: datetime
    host: str
    guard_action: str  # 'Allow' | 'Warn' | 'Block'
    risk_score: float


@dataclass
class SessionContext:
    """Snapshot of prior session activity used by contextual rules.

    `current_event_timestamp` and `current_event_host` describe the request
    being evaluated right now (it is not yet persisted). `prior_events` is the
    chronologically-ordered list of events already stored in the same session
    with timestamp <= current_event_timestamp.

    The legacy fields are retained so existing callers continue to work; new
    contextual rules read only the new fields.
    """
    current_event_timestamp: Optional[datetime] = None
    current_event_host: str = ""
    prior_events: List[PriorEvent] = field(default_factory=list)
    previous_urls: List[str] = field(default_factory=list)
    sensitive_interaction_count: int = 0
    unique_domains_visited: int = 0


# ---------------------------------------------------------------------------
# Scoring thresholds (to be calibrated during model evaluation phase)
# ---------------------------------------------------------------------------

HIGH_RISK_THRESHOLD: float = 0.70   # Score above this → BLOCK
WARN_THRESHOLD: float = 0.25      # Score above this (and below HIGH) → WARN
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
    # Contextual rules (calibration knobs — tune after observing real traffic)
    "sensitive_action_frequency_spike":        0.20,
    "repeated_sensitive_action_after_warning": 0.25,
    "redirect_to_sensitive_action":            0.20,
    "previously_warned_domain_in_session":     0.20,
    # Semantic rules (Stage B — TF-IDF + Logistic Regression, with heuristic fallback)
    "phishing_language":                       0.30,
    "prompt_injection":                        0.30,
}

# ---------------------------------------------------------------------------
# Contextual rule tuning (count caps and time windows for scoring)
# ---------------------------------------------------------------------------

CONTEXTUAL_RULE_CONFIG: Dict[str, Dict[str, Any]] = {
    "sensitive_action_frequency_spike": {
        "max_events": 5,
        "window_ms": 60_000,
    },
    "repeated_sensitive_action_after_warning": {"max_events": 5},
    "redirect_to_sensitive_action": {
        "max_events": 5,
        "redirect_window_ms": 2_000,
    },
    "previously_warned_domain_in_session": {"max_events": 5},
}

# ---------------------------------------------------------------------------
# Semantic rule tuning
# ---------------------------------------------------------------------------
# Each semantic rule binds to a trained classifier (model_id). At runtime the
# classifier produces a probability in [0, 1] used directly as the rule score.
# If no trained model artifact is present, the rule falls back to a
# keyword-based heuristic implemented in `stage_b.heuristics`.

SEMANTIC_RULE_CONFIG: Dict[str, Dict[str, Any]] = {
    "phishing_language": {
        "model_id": "phishing",
        "min_text_chars": 32,
        "trigger_threshold": 0.5,
    },
    "prompt_injection": {
        "model_id": "prompt_injection",
        "min_text_chars": 16,
        # The trained LR is over-confident on benign technical text because the
        # public injection corpora outnumber benign instructions ~25:1. Real
        # injections score 0.99+, so 0.85 leaves headroom while suppressing FPs.
        "trigger_threshold": 0.85,
    },
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


SEMANTIC_RULES: List[RuleDefinition] = [
    RuleDefinition(
        "phishing_language",
        "Phishing or Credential-Harvesting Language",
        RuleType.SEMANTIC, ComputeClass.EXPENSIVE,
        RULE_WEIGHTS["phishing_language"], hard_block=False,
    ),
    RuleDefinition(
        "prompt_injection",
        "Prompt Injection / Instruction Hierarchy Manipulation",
        RuleType.SEMANTIC, ComputeClass.EXPENSIVE,
        RULE_WEIGHTS["prompt_injection"], hard_block=False,
    ),
]


CONTEXTUAL_RULES: List[RuleDefinition] = [
    RuleDefinition(
        "sensitive_action_frequency_spike",
        "Several risky pages in a short time",
        RuleType.CONTEXTUAL, ComputeClass.CHEAP,
        RULE_WEIGHTS["sensitive_action_frequency_spike"], hard_block=False,
    ),
    RuleDefinition(
        "repeated_sensitive_action_after_warning",
        "More risky pages after you were already warned",
        RuleType.CONTEXTUAL, ComputeClass.CHEAP,
        RULE_WEIGHTS["repeated_sensitive_action_after_warning"], hard_block=False,
    ),
    RuleDefinition(
        "redirect_to_sensitive_action",
        "Arrived here through a fast chain of redirects",
        RuleType.CONTEXTUAL, ComputeClass.CHEAP,
        RULE_WEIGHTS["redirect_to_sensitive_action"], hard_block=False,
    ),
    RuleDefinition(
        "previously_warned_domain_in_session",
        "Back to a site we already flagged this session",
        RuleType.CONTEXTUAL, ComputeClass.CHEAP,
        RULE_WEIGHTS["previously_warned_domain_in_session"], hard_block=False,
    ),
]
