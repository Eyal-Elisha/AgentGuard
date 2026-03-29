from __future__ import annotations

from mitmproxy import http

from backend.proxy.filters import (
    is_likely_static_subresource,
    sec_fetch_is_subresource,
    is_binary_media_response,
)


def should_log_request(flow: http.HTTPFlow) -> bool:
    if is_likely_static_subresource(flow.request.pretty_url):
        return False
    if sec_fetch_is_subresource(flow):
        return False
    return True


def should_log_response(flow: http.HTTPFlow) -> bool:
    if not flow.response:
        return False
    if is_likely_static_subresource(flow.request.pretty_url):
        return False
    if sec_fetch_is_subresource(flow):
        return False
    if is_binary_media_response(flow):
        return False
    return True
