"""POSTs the response body to /api/proxy/decision so the DOM-dependent rules run
on real traffic. The page is already in flight so nothing is rewritten; the
call exists to build up the session history the contextual rules need.
"""

from __future__ import annotations

from mitmproxy import http

from backend.proxy.decision_client import post_decision
from backend.proxy.enforcement import BackendDecision
from backend.proxy.utils import build_response_payload


def fetch_backend_response_decision(flow: http.HTTPFlow) -> BackendDecision:
    """Build a response-side payload and forward it to the backend."""
    return post_decision(build_response_payload(flow))
