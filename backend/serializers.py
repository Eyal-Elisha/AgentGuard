"""Serialize SQLite row dicts to API JSON shapes.

May need tweaks (e.g. exposing HTTP method/headers on events) once wired to real HTTP traffic.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def iso_z(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def session_to_dict(row: dict[str, Any]) -> dict:
    return {
        "session_id": row["session_id"],
        "user_id": row["user_id"],
        "start_time": iso_z(row["start_time"]),
        "agent_name": row["agent_name"],
        "end_time": iso_z(row["end_time"]),
        "environment": row["environment"],
    }


def event_to_dict(row: dict[str, Any], include_session: bool = False) -> dict:
    headers: dict[str, Any] | None = None
    raw_headers = row.get("headers_json")
    if isinstance(raw_headers, str):
        try:
            parsed_headers = json.loads(raw_headers)
        except json.JSONDecodeError:
            parsed_headers = raw_headers
        headers = parsed_headers

    out = {
        "event_id": row["event_id"],
        "timestamp": iso_z(row["timestamp"]),
        "url": row["url"],
        "guard_action": row["guard_action"],
        "risk_score": float(row["risk_score"]),
        "http_method": row.get("http_method"),
        "headers": headers,
    }
    if include_session:
        out["session_id"] = row["session_id"]
    return out


def rule_to_dict(row: dict[str, Any]) -> dict:
    return {
        "rule_code": row["rule_code"],
        "weight": float(row["weight"]),
        "rule_type": row["rule_type"],
        "compute_class": row["compute_class"],
        "is_enabled": bool(row["is_enabled"]),
        "is_hard_block": bool(row["is_hard_block"]),
        "description": row["description"],
    }


def analysis_to_dict(row: dict[str, Any]) -> dict:
    return {
        "analysis_id": row["analysis_id"],
        "event_id": row["event_id"],
        "rule_code": row["rule_code"],
        "rule_score": float(row["rule_score"]) if row["rule_score"] is not None else None,
        "details": row["details"],
    }
