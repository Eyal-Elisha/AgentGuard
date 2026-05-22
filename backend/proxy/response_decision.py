"""POST a response (URL + response headers + HTML body) to the backend
`/api/proxy/decision` endpoint so the full Stage A pipeline (DOM-dependent
deterministic rules + session-aware contextual rules) runs on real browsing
traffic.

Unlike `request_decision.fetch_backend_decision`, the result here is observed
*after* the response has been received from the upstream server. We do not
rewrite the response based on it (the page is already in flight); the call
exists so that AgentGuard's session/event history accumulates across pages,
which is what the contextual rules need to fire.
"""

from __future__ import annotations

from mitmproxy import http

from backend.proxy.decision_client import fetch_backend_decision as _fetch_backend_decision
from backend.proxy.enforcement import BackendDecision
from backend.proxy.utils import build_response_payload


def fetch_backend_response_decision(flow: http.HTTPFlow) -> BackendDecision:
    """Build a response-side payload and forward it to the backend."""
    return _fetch_backend_decision(build_response_payload(flow))
