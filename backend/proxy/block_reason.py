"""Compose browser-visible block reasons."""

from __future__ import annotations

from typing import Any, Dict

from .enforcement import build_backend_block_reason
from .session_enforcement_response import session_enforcement_reason


def combined_block_reason(
    data: Dict[str, Any],
    evaluation: Dict[str, Any] | None,
) -> str:
    event_reason = build_backend_block_reason(evaluation)
    session_reason = session_enforcement_reason(data)
    # if not session_reason:
    #     return event_reason
    return f"{event_reason}\n\nSession context:\n{session_reason}"
