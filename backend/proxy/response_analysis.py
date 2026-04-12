"""Stage A in the mitmproxy addon: evaluate HTML response body for eligible flows.
the request-time backend enforcement path. 
This module only scores from the response body for eligible HTML flows.
"""

from __future__ import annotations

import logging

from mitmproxy import http

from backend.analysis.rules import EvaluationResult

from backend.proxy.filters.response_eligibility_filter import should_ignore_response
from backend.proxy.rule_engine import evaluate_http_payload

_logger = logging.getLogger(__name__)


def analyze_response(flow: http.HTTPFlow) -> EvaluationResult | None:
    _logger.debug(f"[AgentGuard] analyze_response called for url={flow.request.pretty_url}")
    ignored = should_ignore_response(flow)
    _logger.debug(f"[AgentGuard] should_ignore_response => {ignored}")

    if ignored:
        return None

    headers = dict(flow.response.headers)
    body = flow.response.content or b""
    status = getattr(flow.response, 'status_code', None)

    _logger.debug(f"[AgentGuard] analyze_response: url={flow.request.pretty_url} status={status} body_len={len(body)}")
    print(f"[AgentGuard] analyze_response entry url={flow.request.pretty_url} eligible={not ignored} status={status} body_len={len(body)}")

    return evaluate_http_payload(
        url=flow.request.pretty_url,
        method=flow.request.method,
        headers=headers,
        body=body,
    )


def analyze_response_safe(flow: http.HTTPFlow) -> EvaluationResult | None:
    try:
        return analyze_response(flow)
      
    except Exception:
        _logger.exception("[AgentGuard] Stage A failed in safe wrapper")
        return None

