from __future__ import annotations

import os
from typing import Any

from mitmproxy import http

_AGENT_HEADERS = ("x-agentguard-agent", "x-agent-name")
_ENV_PROXY_AGENT_NAME = "AGENTGUARD_PROXY_AGENT_NAME"


def _clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def request_agent_name(flow: http.HTTPFlow) -> str | None:
    for header_name in _AGENT_HEADERS:
        value = _clean(flow.request.headers.get(header_name))
        if value is not None:
            return value
    return _clean(os.getenv(_ENV_PROXY_AGENT_NAME))
