"""Decides whether request/response traffic should be logged in the proxy."""

from __future__ import annotations

from mitmproxy import http

from backend.proxy.filters.response_eligibility_filter import is_subresource_or_media


def should_log_request(flow: http.HTTPFlow) -> bool:
    if is_subresource_or_media(flow, include_binary=False):
        return False
    return True


def should_log_response(flow: http.HTTPFlow) -> bool:
    if not flow.response:
        return False
    if is_subresource_or_media(flow, include_binary=True):
        return False
    return True