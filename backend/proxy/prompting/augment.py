"""Append AgentGuard fallback guidance to user prompts in JSON request bodies."""

from __future__ import annotations

import json
from typing import Any

from .payload import augment_payload


def augment_request_body(request: Any) -> None:
    content_type = str(getattr(request, "headers", {}).get("content-type", "")).lower()
    if "application/json" not in content_type:
        return
    get_text = getattr(request, "get_text", None)
    if not callable(get_text):
        return
    try:
        raw = get_text()
        payload = json.loads(raw)
    except Exception:
        return
    if not augment_payload(payload):
        return
    updated = json.dumps(payload, ensure_ascii=False)
    set_text = getattr(request, "set_text", None)
    if callable(set_text):
        set_text(updated)
        return
    request.content = updated.encode("utf-8", errors="replace")

