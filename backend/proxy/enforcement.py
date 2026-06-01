from __future__ import annotations

from dataclasses import dataclass
import html
import json
from typing import Any, Dict
from urllib.parse import urlsplit

from mitmproxy import http

from backend.analysis.rules import Decision
from backend.proxy.block_interstitial import build_block_html
from backend.proxy.warn_bypass import mint_bypass_token
from backend.proxy.warn_interstitial import build_warn_html
from backend.settings import BackendFailureMode, get_backend_failure_mode, get_dashboard_url

_BLOCK_RESPONSE_HEADERS = {
    "Content-Type": "text/plain; charset=utf-8",
    "Cache-Control": "no-store",
}
_BLOCK_HTML_RESPONSE_HEADERS = {
    "Content-Type": "text/html; charset=utf-8",
    "Cache-Control": "no-store",
    "X-AgentGuard-Decision": Decision.BLOCK.value,
}
_WARN_RESPONSE_HEADERS = {
    "Content-Type": "text/html; charset=utf-8",
    "Cache-Control": "no-store",
    "X-AgentGuard-Decision": Decision.WARN.value,
}
_BLOCK_STATUS_CODE = 403
_WARN_STATUS_CODE = 200
_FAIL_CLOSED_STATUS_CODE = 503
_BLOCK_SUMMARY = "AgentGuard blocked the request before it reached the external destination."
_FAIL_CLOSED_SUMMARY = "AgentGuard blocked the request because the decision service is unavailable."
_BACKEND_FAILURE_SOURCES = frozenset({"backend_timeout", "backend_unreachable", "backend_error"})


@dataclass(frozen=True)
class BackendDecision:
    decision: Decision
    reason: str
    evaluation: Dict[str, Any] | None
    source: str
    passive_mode: bool = False

    def as_log_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "source": self.source,
            "evaluation": self.evaluation,
        }


def _detail_from_evaluation(evaluation: Dict[str, Any] | None) -> str | None:
    if not evaluation:
        return None
    rules = evaluation.get("rule_results")
    if not isinstance(rules, list):
        return None

    def _skip_explanation(text: str) -> bool:
        return text.startswith("Skipped")

    for item in rules:
        if not isinstance(item, dict):
            continue
        if item.get("triggered") and item.get("hard_block"):
            explanation = item.get("explanation")
            if isinstance(explanation, str) and explanation and not _skip_explanation(explanation):
                return explanation

    details: list[str] = []
    for item in rules:
        if not isinstance(item, dict) or not item.get("triggered"):
            continue
        explanation = item.get("explanation")
        if isinstance(explanation, str) and explanation and not _skip_explanation(explanation):
            details.append(explanation)
    if not details:
        return None
    return "; ".join(details[:3])


def build_backend_block_reason(evaluation: Dict[str, Any] | None) -> str:
    detail = _detail_from_evaluation(evaluation)
    if detail:
        return f"{_BLOCK_SUMMARY}\n\nReason: {detail}"
    return _BLOCK_SUMMARY


def decision_reason(decision: Decision) -> str:
    if decision == Decision.BLOCK:
        return _BLOCK_SUMMARY
    if decision == Decision.WARN:
        return "AgentGuard marked the request as warn and allowed it to continue."
    return "AgentGuard approved the request."


def local_rule_block_decision(
    *,
    rule_id: str,
    explanation: str,
    source: str,
) -> BackendDecision:
    return BackendDecision(
        decision=Decision.BLOCK,
        reason=f"{_BLOCK_SUMMARY}\n\nReason: {explanation}",
        evaluation={
            "decision": "block",
            "risk_score": 1.0,
            "hard_block_triggered": True,
            "stage_b_required": False,
            "rule_results": [
                {
                    "rule_id": rule_id,
                    "rule_type": "deterministic",
                    "score": 1.0,
                    "hard_block": True,
                    "explanation": explanation,
                    "triggered": True,
                }
            ],
        },
        source=source,
    )


def backend_failure_reason(source: str) -> str:
    if source == "backend_timeout":
        return _FAIL_CLOSED_SUMMARY
    if source == "backend_unreachable":
        return _FAIL_CLOSED_SUMMARY
    if source == "backend_error":
        return "AgentGuard blocked the request because the decision service returned an invalid response."
    return _FAIL_CLOSED_SUMMARY


def failure_decision(*, source: str, reason: str) -> BackendDecision:
    failure_mode = get_backend_failure_mode()
    if failure_mode == BackendFailureMode.FAIL_OPEN:
        return BackendDecision(
            decision=Decision.ALLOW,
            reason="AgentGuard allowed the request because fail-open mode is enabled.",
            evaluation=None,
            source=source,
        )
    return BackendDecision(
        decision=Decision.BLOCK,
        reason=reason,
        evaluation=None,
        source=source,
    )


def _build_block_response(
    *,
    status_code: int,
    decision: Decision,
    reason: str,
) -> http.Response:
    headers = dict(_BLOCK_RESPONSE_HEADERS)
    headers["X-AgentGuard-Decision"] = decision.value
    return http.Response.make(status_code, reason, headers)


def build_enforcement_response(decision: BackendDecision) -> http.Response:
    if decision.decision == Decision.BLOCK and decision.source not in _BACKEND_FAILURE_SOURCES:
        return _build_block_response(
            status_code=_BLOCK_STATUS_CODE,
            decision=decision.decision,
            reason=decision.reason,
        )
    return _build_block_response(
        status_code=_FAIL_CLOSED_STATUS_CODE,
        decision=Decision.BLOCK,
        reason=decision.reason,
    )


def is_backend_failure_source(source: str) -> bool:
    return source in _BACKEND_FAILURE_SOURCES


def _reason_code(*, original_url: str, decision: BackendDecision) -> str:
    evaluation = decision.evaluation if isinstance(decision.evaluation, dict) else None
    if isinstance(evaluation, dict):
        rules = evaluation.get("rule_results")
        if isinstance(rules, list):
            for item in rules:
                if not isinstance(item, dict) or not item.get("triggered"):
                    continue
                rid = str(item.get("rule_id", "")).strip().lower()
                if rid:
                    if rid == "custom_blacklist":
                        return "custom_blacklist"
                    return f"rule:{rid}"

    if original_url.lower().startswith("http://"):
        return "unencrypted_http"

    lowered_reason = (decision.reason or "").lower()
    if "decision service is unavailable" in lowered_reason or decision.source in _BACKEND_FAILURE_SOURCES:
        return "backend_unavailable"
    if "invalid response" in lowered_reason:
        return "backend_invalid_response"
    return "policy_block"


def _constraints(*, original_url: str, decision: BackendDecision) -> Dict[str, Any]:
    constraints: Dict[str, Any] = {}
    if original_url.lower().startswith("http://"):
        constraints["require_https"] = True

    try:
        host = (urlsplit(original_url).hostname or "").strip().lower()
    except ValueError:
        host = ""
    if host:
        constraints["forbidden_hosts"] = [host]
    return constraints


def _risk_payload(evaluation: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(evaluation, dict):
        return {"score": None, "hard_block_triggered": None}
    score = evaluation.get("risk_score")
    hard_block = evaluation.get("hard_block_triggered")
    normalized_score = float(score) if isinstance(score, (int, float)) else None
    normalized_hard_block = bool(hard_block) if isinstance(hard_block, bool) else None
    return {
        "score": normalized_score,
        "hard_block_triggered": normalized_hard_block,
    }


def build_browseros_block_response(*, original_url: str, decision: BackendDecision) -> http.Response:
    payload = {
        "decision": Decision.BLOCK.value,
        "enforcement_mode": "soft_block",
        "blocked_url": original_url,
        "reason_code": _reason_code(original_url=original_url, decision=decision),
        "reason": decision.reason,
        "risk": _risk_payload(decision.evaluation),
        "retryable": True,
        "constraints": _constraints(original_url=original_url, decision=decision),
        "safe_alternatives": [{"type": "navigate", "url": get_dashboard_url(), "label": "AgentGuard dashboard"}],
        "cooldown_seconds": 30,
    }
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
        "X-AgentGuard-Decision": Decision.BLOCK.value,
        "X-AgentGuard-Continuation": "available",
    }
    return http.Response.make(_BLOCK_STATUS_CODE, json.dumps(payload), headers)


def build_browseros_recovery_response(*, original_url: str, decision: BackendDecision) -> http.Response:
    auto_target = get_dashboard_url()
    rows = [f'<li><a href="{html.escape(auto_target)}">Open AgentGuard dashboard</a></li>']

    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AgentGuard Recovery</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; line-height: 1.5; }}
    .panel {{ max-width: 760px; margin: 0 auto; border: 1px solid #ddd; border-radius: 12px; padding: 20px; }}
    h1 {{ margin-top: 0; }}
    .muted {{ color: #555; }}
    ul {{ padding-left: 20px; }}
    a {{ color: #0b57d0; }}
  </style>
</head>
<body>
  <main class="panel">
    <h1>Blocked destination detected</h1>
    <p class="muted">AgentGuard blocked direct access to <strong>{html.escape(original_url)}</strong>.</p>
    <p><strong>Continue the same task using a safer alternative below.</strong></p>
    <ul>
      {''.join(rows)}
    </ul>
    <p class="muted">Auto-continuing in 3 seconds to: {html.escape(auto_target)}</p>
  </main>
  <script>setTimeout(function(){{ window.location.href = {json.dumps(auto_target)}; }}, 3000);</script>
</body>
</html>"""

    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-store",
        "X-AgentGuard-Decision": Decision.BLOCK.value,
        "X-AgentGuard-Continuation": "available",
        "X-AgentGuard-Recovery-Mode": "guided",
    }
    return http.Response.make(200, body, headers)


def _reason_text_for_block(decision: BackendDecision) -> str:
    """Strip the boilerplate `_BLOCK_SUMMARY` prefix so the interstitial
    only shows the *specific* reason. Falls back to the raw reason if
    we can't parse it."""
    raw = (decision.reason or "").strip()
    marker = "Reason:"
    if marker in raw:
        return raw.split(marker, 1)[1].strip()
    if raw.startswith(_BLOCK_SUMMARY):
        rest = raw[len(_BLOCK_SUMMARY):].strip()
        return rest or raw
    return raw


def build_block_response(
    *, original_url: str, decision: BackendDecision
) -> http.Response:
    """Return an HTML interstitial response for a hard Block decision.

    Use this only for GET navigations where a browser will actually render
    the body. For sub-resources / XHR / fail-closed paths, callers should
    keep using `build_enforcement_response` so the response stays a plain
    403/503 text body.
    """
    evaluation = decision.evaluation if isinstance(decision.evaluation, dict) else None
    body = build_block_html(
        original_url=original_url,
        reason=_reason_text_for_block(decision),
        evaluation=evaluation,
        safe_back_url=get_dashboard_url(),
    )
    headers = dict(_BLOCK_HTML_RESPONSE_HEADERS)
    return http.Response.make(_BLOCK_STATUS_CODE, body, headers)


def build_warn_response(
    *, original_url: str, host: str, decision: BackendDecision
) -> http.Response:
    """Return an interstitial HTML response for a Warn decision.

    The response sets the bypass cookie via a `Set-Cookie` header so the
    browser stores it automatically. Clicking "Continue anyway" only needs
    to navigate — no JS cookie write required.
    """
    token = mint_bypass_token(host)
    evaluation = decision.evaluation if isinstance(decision.evaluation, dict) else None
    risk_score: float | None = None
    if isinstance(evaluation, dict):
        candidate = evaluation.get("risk_score")
        if isinstance(candidate, (int, float)):
            risk_score = float(candidate)
    body = build_warn_html(
        original_url=original_url,
        bypass_token=token,
        risk_score=risk_score,
        evaluation=evaluation,
        safe_back_url=get_dashboard_url(),
    )
    headers = dict(_WARN_RESPONSE_HEADERS)
    return http.Response.make(_WARN_STATUS_CODE, body, headers)


def build_warn_body(
    *, original_url: str, host: str, decision: BackendDecision
) -> tuple[bytes, dict[str, str]]:
    """Return the (body, headers) tuple used to overwrite an existing response.

    Used by the response-time path in `handle_response`, where `flow.response`
    already exists and only its content/headers need to be rewritten.
    """
    token = mint_bypass_token(host)
    evaluation = decision.evaluation if isinstance(decision.evaluation, dict) else None
    risk_score: float | None = None
    if isinstance(evaluation, dict):
        candidate = evaluation.get("risk_score")
        if isinstance(candidate, (int, float)):
            risk_score = float(candidate)
    body = build_warn_html(
        original_url=original_url,
        bypass_token=token,
        risk_score=risk_score,
        evaluation=evaluation,
        safe_back_url=get_dashboard_url(),
    )
    headers = dict(_WARN_RESPONSE_HEADERS)
    return body, headers
