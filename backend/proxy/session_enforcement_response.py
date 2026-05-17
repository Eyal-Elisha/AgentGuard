"""Read session-enforcement metadata from backend decision responses."""

from __future__ import annotations

from typing import Any, Dict


def session_enforcement_level(data: Dict[str, Any]) -> str | None:
    enforcement = data.get("session_enforcement")
    if not isinstance(enforcement, dict):
        return None
    level = enforcement.get("level")
    return level if isinstance(level, str) else None


def session_enforcement_reason(data: Dict[str, Any]) -> str | None:
    enforcement = data.get("session_enforcement")
    if not isinstance(enforcement, dict):
        return None
    for field in ("reason", "message"):
        value = enforcement.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return None
