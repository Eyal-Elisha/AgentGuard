from __future__ import annotations

from mitmproxy import http

from backend.proxy.decision_client import post_decision
from backend.proxy.enforcement import BackendDecision
from backend.proxy.utils import build_request_data


def fetch_backend_decision(flow: http.HTTPFlow) -> BackendDecision:
    """Build the outbound payload and delegate backend decision fetching."""
    return post_decision(build_request_data(flow))
