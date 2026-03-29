"""Stage A in the mitmproxy addon: evaluate when the HTML response is available.

Typical flow: browser GET → server returns HTML → `response` hook runs with the page body.
That is *before* the next user/agent action on that document (typing, submitting). Rules that
need DOM (forms, text) run here.

A separate problem is POST/PUT that *already carry* secrets in the body: those are handled by
the request-time backend enforcement path. This module only scores from the response body for
eligible HTML flows.
"""

from __future__ import annotations

import logging

from mitmproxy import http

from backend.analysis.rules import EvaluationResult
from backend.proxy.filters.analysis_eligibility import is_eligible_for_response_analysis
from backend.proxy.policy_engine import evaluate_http_payload

_logger = logging.getLogger(__name__)


def analyze_response(flow: http.HTTPFlow) -> EvaluationResult | None:
    if not is_eligible_for_response_analysis(flow):
        return None
    if not flow.response:
        return None

    headers = dict(flow.response.headers)
    body = flow.response.content or b""
    return evaluate_http_payload(
        url=flow.request.pretty_url,
        method=flow.request.method,
        headers=headers,
        body=body,
    )


def analyze_response_safe(flow: http.HTTPFlow) -> EvaluationResult | None:
    """Like analyze_response but logs failures instead of propagating."""
    try:
        return analyze_response(flow)
    except Exception:
        _logger.exception("[AgentGuard] Stage A failed")
        return None
