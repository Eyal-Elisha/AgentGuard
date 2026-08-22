"""What the proxy records about the traffic it decided on: the encrypted journal,
agent names, sessions, and decisions with their per-rule analyses.
"""

from .agents import (
    AGENT_CATALOGUE,
    DEFAULT_AGENT_NAME,
    is_catalogue_agent,
    normalize_proxy_agent_name,
)
from .decisions import record_proxy_decision
from .sessions import (
    close_proxy_session,
    ensure_proxy_session_started,
    resolve_proxy_session_id,
)

__all__ = [
    "AGENT_CATALOGUE",
    "DEFAULT_AGENT_NAME",
    "close_proxy_session",
    "ensure_proxy_session_started",
    "is_catalogue_agent",
    "normalize_proxy_agent_name",
    "record_proxy_decision",
    "resolve_proxy_session_id",
]
