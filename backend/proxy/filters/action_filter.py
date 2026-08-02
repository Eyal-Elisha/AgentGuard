"""Filters requests by HTTP method to decide what AgentGuard enforces."""

from mitmproxy import http

from backend.validation.proxy_requests import ALLOWED_PROXY_METHODS


def is_enforced_request_method(flow: http.HTTPFlow) -> bool:
    """Methods that AgentGuard actively inspects in the proxy pipeline."""
    return flow.request.method.upper() in ALLOWED_PROXY_METHODS
