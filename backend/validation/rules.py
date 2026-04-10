"""Rule and rule-analysis validation."""

from __future__ import annotations

from typing import Any

from .common import (
    ALLOWED_COMPUTE_CLASSES,
    ALLOWED_RULE_TYPES,
    clean_string,
    parse_bounded_float,
    parse_positive_int,
    require_dict,
)


def validate_rule_payload(payload: dict | None, partial: bool = False) -> tuple[dict | None, str | None]:
    payload, err = require_dict(payload)
    if err:
        return None, err

    fields = [
        "rule_code",
        "weight",
        "rule_type",
        "compute_class",
        "is_enabled",
        "is_hard_block",
        "description",
    ]
    data: dict[str, Any] = {}
    for key in fields:
        if key not in payload:
            if not partial:
                return None, f"Missing {key}"
            continue
        data[key] = payload[key]

    if not partial or "rule_code" in data:
        rule_code = clean_string(data.get("rule_code"), max_length=30)
        if rule_code is None:
            return None, "Invalid rule_code"
        data["rule_code"] = rule_code

    if not partial or "weight" in data:
        weight = parse_bounded_float(data.get("weight"), minimum=0)
        if weight is None:
            return None, "Invalid weight"
        data["weight"] = weight

    if not partial or "rule_type" in data:
        rule_type = data.get("rule_type")
        if not isinstance(rule_type, str) or rule_type not in ALLOWED_RULE_TYPES:
            return None, "Invalid rule_type"

    if not partial or "compute_class" in data:
        compute_class = data.get("compute_class")
        if not isinstance(compute_class, str) or compute_class not in ALLOWED_COMPUTE_CLASSES:
            return None, "Invalid compute_class"

    if not partial or "is_enabled" in data:
        if not isinstance(data.get("is_enabled"), bool):
            return None, "Invalid is_enabled"

    if not partial or "is_hard_block" in data:
        if not isinstance(data.get("is_hard_block"), bool):
            return None, "Invalid is_hard_block"

    if not partial or "description" in data:
        description = data.get("description")
        if description is None:
            data["description"] = None
        else:
            cleaned_description = clean_string(description, max_length=255)
            if cleaned_description is None:
                return None, "Invalid description"
            data["description"] = cleaned_description

    return data, None


def validate_rules_analysis_list_query(rule_code: Any, limit: Any) -> tuple[dict | None, str | None]:
    cleaned_rule_code = clean_string(rule_code, max_length=30)
    if cleaned_rule_code is None:
        return None, "rule_code is required"

    parsed_limit = parse_positive_int(limit)
    if parsed_limit is None or parsed_limit > 1000:
        return None, "Invalid limit"

    return {"rule_code": cleaned_rule_code, "limit": parsed_limit}, None


def validate_rules_analysis_payload(payload: dict | None) -> tuple[dict | None, str | None]:
    payload, err = require_dict(payload)
    if err:
        return None, err

    event_id = parse_positive_int(payload.get("event_id"))
    rule_code = clean_string(payload.get("rule_code"), max_length=30)
    details = clean_string(payload.get("details"), max_length=255)

    if event_id is None:
        return None, "Invalid event_id"
    if rule_code is None:
        return None, "Invalid rule_code"

    raw_rule_score = payload.get("rule_score")
    if raw_rule_score is None:
        rule_score = None
    else:
        rule_score = parse_bounded_float(raw_rule_score, minimum=0, maximum=1)
        if rule_score is None:
            return None, "Invalid rule_score"

    if details is None:
        return None, "Invalid details"

    return {
        "event_id": event_id,
        "rule_code": rule_code,
        "rule_score": rule_score,
        "details": details,
    }, None


def validate_rule_enabled_payload(payload: dict | None) -> tuple[dict | None, str | None]:
    payload, err = require_dict(payload)
    if err:
        return None, err

    if "is_enabled" not in payload or not isinstance(payload.get("is_enabled"), bool):
        return None, "Invalid is_enabled"

    return {"is_enabled": payload["is_enabled"]}, None
