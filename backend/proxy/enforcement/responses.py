"""Turning a `BackendDecision` into the HTTP response the browser receives.

Which form a block takes depends on what the browser can render. A GET
navigation gets the HTML interstitial; anything else (XHR, a sub-resource, a
fail-closed path) gets a plain-text status body, because a page of HTML in
place of a script or an image is worse than useless.
"""

from __future__ import annotations

from mitmproxy import http

from backend.analysis.rules import Decision
from backend.proxy.interstitials import build_block_html, build_warn_html
from backend.proxy.interstitials.evidence import risk_score_of
from backend.proxy.warn_bypass import mint_bypass_token
from backend.settings import get_dashboard_url

from .decision import BACKEND_FAILURE_SOURCES, BackendDecision
from .reasons import specific_block_reason

_BLOCK_STATUS_CODE = 403
_WARN_STATUS_CODE = 200
_FAIL_CLOSED_STATUS_CODE = 503

_PLAIN_HEADERS = {
    "Content-Type": "text/plain; charset=utf-8",
    "Cache-Control": "no-store",
}
_BLOCK_HTML_HEADERS = {
    "Content-Type": "text/html; charset=utf-8",
    "Cache-Control": "no-store",
    "X-AgentGuard-Decision": Decision.BLOCK.value,
}
_WARN_HTML_HEADERS = {
    "Content-Type": "text/html; charset=utf-8",
    "Cache-Control": "no-store",
    "X-AgentGuard-Decision": Decision.WARN.value,
}


def is_get_navigation(flow: http.HTTPFlow) -> bool:
    """Whether the browser would render an HTML body for this request."""
    return flow.request.method.upper() == "GET"


def block_response_for(flow: http.HTTPFlow, decision: BackendDecision) -> http.Response:
    """The right shape of Block for this flow.

    A GET navigation gets the interstitial. An XHR or sub-resource cannot
    render one, so it gets the plain 403 instead.
    """
    if is_get_navigation(flow):
        return build_block_response(original_url=flow.request.pretty_url, decision=decision)
    return build_enforcement_response(decision)


def build_enforcement_response(decision: BackendDecision) -> http.Response:
    """The plain-text refusal: 403 for a real block, 503 when the backend failed."""
    blocked_by_a_rule = (
        decision.decision == Decision.BLOCK and decision.source not in BACKEND_FAILURE_SOURCES
    )
    status_code = _BLOCK_STATUS_CODE if blocked_by_a_rule else _FAIL_CLOSED_STATUS_CODE
    headers = dict(_PLAIN_HEADERS)
    headers["X-AgentGuard-Decision"] = Decision.BLOCK.value
    return http.Response.make(status_code, decision.reason, headers)


def build_block_response(*, original_url: str, decision: BackendDecision) -> http.Response:
    """The Block interstitial, for GET navigations a browser will render."""
    body = build_block_html(
        original_url=original_url,
        reason=specific_block_reason(decision.reason),
        evaluation=_evaluation_of(decision),
        safe_back_url=get_dashboard_url(),
    )
    return http.Response.make(_BLOCK_STATUS_CODE, body, dict(_BLOCK_HTML_HEADERS))


def build_warn_body(*, original_url: str, host: str, decision: BackendDecision) -> tuple[bytes, dict[str, str]]:
    """The Warn interstitial as `(body, headers)`.

    Response-time enforcement needs these separately: `flow.response` already
    exists at that point, so only its content and headers get overwritten.
    """
    evaluation = _evaluation_of(decision)
    body = build_warn_html(
        original_url=original_url,
        bypass_token=mint_bypass_token(host),
        risk_score=risk_score_of(evaluation),
        evaluation=evaluation,
        safe_back_url=get_dashboard_url(),
    )
    return body, dict(_WARN_HTML_HEADERS)


def build_warn_response(*, original_url: str, host: str, decision: BackendDecision) -> http.Response:
    """The Warn interstitial as a complete response, for request-time enforcement."""
    body, headers = build_warn_body(original_url=original_url, host=host, decision=decision)
    return http.Response.make(_WARN_STATUS_CODE, body, headers)


def _evaluation_of(decision: BackendDecision) -> dict | None:
    return decision.evaluation if isinstance(decision.evaluation, dict) else None
