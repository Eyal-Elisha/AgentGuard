"""SQLite storage surface: one module to import from; logic lives in the smaller *_store files."""

from __future__ import annotations

from .db import database_path
from .schema import init_schema
from .users_store import UsernameTakenError, user_get_by_username, user_create
from .sessions_store import (
    session_try_close,
    session_create,
    session_delete,
    session_get,
    sessions_list_desc,
    session_stats,
    session_update_end,
)
from .events_store import (
    events_list_for_session,
    events_list_all,
    event_get,
    event_create,
)
from .rules_store import rules_list_asc, rule_get, rule_create
from .rules_analysis_store import (
    rule_analysis_list_for_event,
    rule_analysis_create,
    rule_analysis_list_for_rule,
)

__all__ = [
    "database_path",
    "init_schema",
    # Users
    "UsernameTakenError",
    "user_get_by_username",
    "user_create",
    # Sessions
    "sessions_list_desc",
    "session_get",
    "session_create",
    "session_update_end",
    "session_try_close",
    "session_delete",
    "session_stats",
    # Events
    "events_list_for_session",
    "events_list_all",
    "event_get",
    "event_create",
    # Rules
    "rules_list_asc",
    "rule_get",
    "rule_create",
    # Rules analysis
    "rule_analysis_list_for_event",
    "rule_analysis_create",
    "rule_analysis_list_for_rule",
]