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


def is_eligible_for_response_analysis(flow: http.HTTPFlow) -> bool:

    if not flow.response:
        return False

    status = flow.response.status_code
    if not (200 <= status < 300):
        return False

    if is_likely_static_subresource(flow.request.pretty_url):
        return False
    if sec_fetch_is_subresource(flow):
        return False

    if is_binary_media_response(flow):
        return False

    ua = flow.request.headers.get("user-agent", "")
    if not is_browser_user_agent(ua):
        return False
    if is_noise(flow):
        return False

    if is_action_request(flow):
        return _has_response_body(flow)

    if flow.request.method.upper() != "GET":
        return False

    return True
