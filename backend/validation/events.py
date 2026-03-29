"""Event payload and query validation."""

from __future__ import annotations

from typing import Any

from .common import (
    ALLOWED_GUARD_ACTIONS,
    clean_string,
    parse_bounded_float,
    parse_iso_datetime,
    require_dict,
)


def validate_event_payload(payload: dict | None) -> tuple[dict | None, str | None]:
    payload, err = require_dict(payload)
    if err:
        return None, err

    url = clean_string(payload.get("url"))
    headers = payload.get("headers")
    method = clean_string(payload.get("method"), max_length=16)
    timestamp = parse_iso_datetime(payload.get("timestamp"))
    guard_action = payload.get("guard_action")
    risk_score = parse_bounded_float(payload.get("risk_score"), minimum=0, maximum=1)

    errors: list[str] = []
    if url is None:
        errors.append("url")
    if headers is None:
        errors.append("headers")
    elif not isinstance(headers, dict):
        errors.append("headers must be an object")
    if method is None:
        errors.append("method")
    if timestamp is None:
        errors.append("timestamp")
    if not isinstance(guard_action, str) or guard_action not in ALLOWED_GUARD_ACTIONS:
        errors.append("guard_action")
    if risk_score is None:
        errors.append("risk_score")

    if errors:
        return None, "Invalid payload: " + ", ".join(errors)

    return {
        "url": url,
        "headers": headers,
        "method": method.upper(),
        "timestamp": timestamp,
        "guard_action": guard_action,
        "risk_score": risk_score,
    }, None


def parse_event_filters(args: dict[str, Any]) -> tuple[dict | None, str | None]:
    lowered_args = {str(key).lower(): args[key] for key in args}

    guard_action = lowered_args.get("guard_action")
    if guard_action is not None and guard_action not in ALLOWED_GUARD_ACTIONS:
        return None, "Invalid guard_action"

    min_risk_score = parse_bounded_float(lowered_args.get("min_risk_score"), minimum=0, maximum=1)
    max_risk_score = parse_bounded_float(lowered_args.get("max_risk_score"), minimum=0, maximum=1)
    if "min_risk_score" in lowered_args and min_risk_score is None:
        return None, "Invalid query parameters"
    if "max_risk_score" in lowered_args and max_risk_score is None:
        return None, "Invalid query parameters"
    if min_risk_score is not None and max_risk_score is not None and min_risk_score > max_risk_score:
        return None, "Invalid query parameters"

    from_timestamp = to_timestamp = None
    if "from_timestamp" in lowered_args:
        from_timestamp = parse_iso_datetime(lowered_args["from_timestamp"])
        if from_timestamp is None:
            return None, "Invalid from_timestamp"
    if "to_timestamp" in lowered_args:
        to_timestamp = parse_iso_datetime(lowered_args["to_timestamp"])
        if to_timestamp is None:
            return None, "Invalid to_timestamp"
    if from_timestamp is not None and to_timestamp is not None and from_timestamp > to_timestamp:
        return None, "Invalid query parameters"

    return {
        "guard_action": guard_action,
        "min_risk_score": min_risk_score,
        "max_risk_score": max_risk_score,
        "from_timestamp": from_timestamp,
        "to_timestamp": to_timestamp,
    }, None
