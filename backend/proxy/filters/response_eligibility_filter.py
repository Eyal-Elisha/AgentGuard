"""Combines filter signals to decide whether a response should be ignored."""

from __future__ import annotations

from mitmproxy import http

from .static_filter import is_likely_static_subresource
from .sec_fetch_filter import sec_fetch_is_subresource
from .content_type_filter import is_binary_media_response
from .browser_filter import is_browser_user_agent
from .noise_filter import is_noise
from .action_filter import is_action_request


def _has_response_body(flow: http.HTTPFlow) -> bool:
    if not flow.response:
        return False
    return bool(flow.response.content)


def is_subresource_or_media(flow: http.HTTPFlow, *, include_binary: bool) -> bool:
    if is_likely_static_subresource(flow.request.pretty_url):
        return True
    if sec_fetch_is_subresource(flow):
        return True
    if include_binary and is_binary_media_response(flow):
        return True
    return False


def should_ignore_response(flow: http.HTTPFlow) -> bool:
    if not flow.response:
        return True

    status = flow.response.status_code
    if not (200 <= status < 300):
        return True

    if is_subresource_or_media(flow, include_binary=True):
        return True

    if not is_browser_user_agent(flow.request.headers.get("user-agent", "")):
        return True
        
    if is_noise(flow):
        return True

    if is_action_request(flow):
        return not _has_response_body(flow)

    if flow.request.method.upper() != "GET":
        return True

    return False
