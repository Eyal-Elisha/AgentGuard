"""Configuration for session risk scoring."""

from __future__ import annotations

RECENT_EVENT_LIMIT = 5
RISKY_EVENT_THRESHOLD = 0.40
TREND_DELTA = 0.15

RISK_WEIGHTS = {
    "highest_event": 0.45,
    "recent_weighted": 0.25,
    "risky_event_count": 0.15,
    "warn_block": 0.10,
    "sensitive_interaction": 0.05,
}

SENSITIVE_RULE_CODES = frozenset(
    {
        "sensitive_fields",
        "external_form_action",
        "unexpected_redirect",
        "brand_domain_mismatch",
    }
)

LOW_RISK_LIMIT = 0.40
MEDIUM_RISK_LIMIT = 0.60
HIGH_RISK_LIMIT = 0.80

MAX_RISKY_EVENTS = 5
MAX_WARN_BLOCK_POINTS = 5
MAX_SENSITIVE_INTERACTIONS = 3
