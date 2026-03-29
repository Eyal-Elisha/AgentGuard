from mitmproxy import http

_ENFORCED_REQUEST_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})


def is_enforced_request_method(flow: http.HTTPFlow) -> bool:
    """Methods that AgentGuard actively inspects in the proxy pipeline."""
    return flow.request.method.upper() in _ENFORCED_REQUEST_METHODS


def is_action_request(flow: http.HTTPFlow) -> bool:
    """Backward-compatible alias for older imports/tests."""
    return is_enforced_request_method(flow)
