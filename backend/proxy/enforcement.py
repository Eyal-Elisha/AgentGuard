from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from mitmproxy import http

from backend.analysis.rules import Decision
from backend.settings import BackendFailureMode, get_backend_failure_mode

_BLOCK_RESPONSE_HEADERS = {
    "Content-Type": "text/plain; charset=utf-8",
    "Cache-Control": "no-store",
}
_BLOCK_STATUS_CODE = 403
_FAIL_CLOSED_STATUS_CODE = 503
_BLOCK_SUMMARY = "AgentGuard blocked the request before it reached the external destination."
_FAIL_CLOSED_SUMMARY = "AgentGuard blocked the request because the decision service is unavailable."


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
    if decision.decision == Decision.BLOCK and decision.source == "backend":
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
