from __future__ import annotations

from mitmproxy import http

from backend.proxy.decision_client import fetch_backend_decision as _fetch_backend_decision
from backend.proxy.enforcement import BackendDecision, build_enforcement_response
from backend.proxy.utils import build_request_data


def fetch_backend_decision(flow: http.HTTPFlow) -> BackendDecision:
    """Build the outbound payload and delegate backend decision fetching."""
    return _fetch_backend_decision(build_request_data(flow))
