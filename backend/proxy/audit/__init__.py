"""What the proxy records about the traffic it decided on.

  journal    the encrypted append-only log every record ends up in
  agents     canonical agent names
  sessions   opening, resolving and closing a proxy session
  decisions  persisting one decision and its per-rule analyses
"""

from .agents import normalize_proxy_agent_name
from .decisions import record_proxy_decision
from .sessions import (
    close_proxy_session,
    ensure_proxy_session_started,
    resolve_proxy_session_id,
)

__all__ = [
    "close_proxy_session",
    "ensure_proxy_session_started",
    "normalize_proxy_agent_name",
    "record_proxy_decision",
    "resolve_proxy_session_id",
]
