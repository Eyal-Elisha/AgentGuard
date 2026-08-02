"""How the proxy acts on a verdict.

`decision` holds the verdict type and the ways one gets built, `reasons` the
text that explains it to a human, and `responses` the HTTP the browser
actually receives.
"""

from .decision import (
    BACKEND_FAILURE_SOURCES,
    BackendDecision,
    failure_decision,
    local_rule_block_decision,
)
from .reasons import backend_failure_reason, build_backend_block_reason, decision_reason
from .responses import (
    build_block_response,
    build_enforcement_response,
    build_warn_body,
    build_warn_response,
)

__all__ = [
    "BACKEND_FAILURE_SOURCES",
    "BackendDecision",
    "backend_failure_reason",
    "build_backend_block_reason",
    "build_block_response",
    "build_enforcement_response",
    "build_warn_body",
    "build_warn_response",
    "decision_reason",
    "failure_decision",
    "local_rule_block_decision",
]
