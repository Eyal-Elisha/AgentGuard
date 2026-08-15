"""How the proxy acts on a verdict: `decision` is the verdict itself, `reasons`
the text explaining it, `responses` the HTTP the browser receives.
"""

from .decision import (
    BACKEND_FAILURE_SOURCES,
    BackendDecision,
    failure_decision,
    local_rule_block_decision,
)
from .reasons import backend_failure_reason, build_backend_block_reason, decision_reason
from .responses import (
    block_response_for,
    build_block_response,
    build_enforcement_response,
    build_warn_body,
    build_warn_response,
    is_get_navigation,
)

__all__ = [
    "BACKEND_FAILURE_SOURCES",
    "BackendDecision",
    "backend_failure_reason",
    "block_response_for",
    "build_backend_block_reason",
    "build_block_response",
    "build_enforcement_response",
    "build_warn_body",
    "build_warn_response",
    "decision_reason",
    "failure_decision",
    "is_get_navigation",
    "local_rule_block_decision",
]
