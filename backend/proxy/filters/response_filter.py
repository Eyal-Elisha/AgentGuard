from __future__ import annotations

from mitmproxy import http

from .response_logging import (
    should_log_request,
    should_log_response,
)
from .browser_filter import is_browser_user_agent
from .noise_filter import is_noise
from .action_filter import is_action_request


def is_browser_traffic(flow: http.HTTPFlow) -> bool:
    ua = flow.request.headers.get("user-agent", "")
    if not is_browser_user_agent(ua):
        return False
    if is_noise(flow):
        return False
    return is_action_request(flow)


__all__ = [
    "should_log_request",
    "should_log_response",
    "is_browser_traffic",
]
