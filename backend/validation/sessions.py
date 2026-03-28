"""Session payload validation."""

from __future__ import annotations

from .common import ALLOWED_ENVIRONMENTS, clean_string, parse_iso_datetime, require_dict


def validate_create_session(payload: dict | None) -> tuple[dict | None, str | None]:
    payload, err = require_dict(payload)
    if err:
        return None, err

    start_time = parse_iso_datetime(payload.get("start_time"))
    agent_name = clean_string(payload.get("agent_name"), max_length=20)
    environment = payload.get("environment")

    if start_time is None:
        return None, "Invalid or missing start_time"
    if agent_name is None:
        return None, "Missing agent_name"
    if not isinstance(environment, str) or environment not in ALLOWED_ENVIRONMENTS:
        return None, "Invalid environment value"

    return {
        "start_time": start_time,
        "agent_name": agent_name,
        "environment": environment,
    }, None


def validate_update_session(payload: dict | None) -> tuple[dict | None, str | None]:
    payload, err = require_dict(payload)
    if err:
        return None, err
    if "end_time" not in payload:
        return None, "end_time is required"

    end_time = parse_iso_datetime(payload.get("end_time"))
    if end_time is None:
        return None, "Invalid end_time"

    return {"end_time": end_time}, None
