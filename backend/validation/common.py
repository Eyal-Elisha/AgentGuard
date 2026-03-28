"""Shared validation constants and parsing helpers."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

ALLOWED_ENVIRONMENTS = frozenset({"test", "prod"})
ALLOWED_GUARD_ACTIONS = frozenset({"Allow", "Warn", "Block"})
ALLOWED_RULE_TYPES = frozenset({"deterministic", "contextual", "semantic"})
ALLOWED_COMPUTE_CLASSES = frozenset({"cheap", "expensive"})


def invalid_json() -> tuple[None, str]:
    return None, "Invalid JSON body"


def require_dict(payload: dict | None) -> tuple[dict, None] | tuple[None, str]:
    if not isinstance(payload, dict):
        return invalid_json()
    return payload, None


def parse_iso_datetime(value: Any) -> datetime | None:
    if value is None or not isinstance(value, str):
        return None
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def clean_string(value: Any, *, max_length: int | None = None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if max_length is not None and len(cleaned) > max_length:
        return None
    return cleaned


def parse_bounded_float(
    value: Any,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    if minimum is not None and parsed < minimum:
        return None
    if maximum is not None and parsed > maximum:
        return None
    return parsed


def parse_positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 1:
        return None
    return parsed
