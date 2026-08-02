"""The human-readable text that explains an enforcement outcome.

These strings surface in three places — the plain-text 403/503 body, the
interstitial pages, and the proxy log — so they are kept together and free of
any dependency on the decision or response types.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.analysis.rules import Decision

BLOCK_SUMMARY = "AgentGuard blocked the request before it reached the external destination."
FAIL_CLOSED_SUMMARY = "AgentGuard blocked the request because the decision service is unavailable."

_INVALID_RESPONSE_SUMMARY = (
    "AgentGuard blocked the request because the decision service returned an invalid response."
)
_REASON_MARKER = "Reason:"

# Rules that were never executed record a "Skipped ..." explanation; those
# would read as noise in a block message, so they are filtered out.
_SKIPPED_PREFIX = "Skipped"


def _explanations(evaluation: Optional[Dict[str, Any]], *, hard_block_only: bool) -> list[str]:
    if not isinstance(evaluation, dict):
        return []
    rules = evaluation.get("rule_results")
    if not isinstance(rules, list):
        return []

    out: list[str] = []
    for item in rules:
        if not isinstance(item, dict) or not item.get("triggered"):
            continue
        if hard_block_only and not item.get("hard_block"):
            continue
        explanation = item.get("explanation")
        if isinstance(explanation, str) and explanation and not explanation.startswith(_SKIPPED_PREFIX):
            out.append(explanation)
    return out


def _detail_from_evaluation(evaluation: Optional[Dict[str, Any]]) -> Optional[str]:
    """The most useful one-line detail available in an evaluation.

    A hard block is the reason on its own, so it wins outright. Otherwise the
    block came from the aggregate score and up to three contributing rules are
    listed.
    """
    hard_blocks = _explanations(evaluation, hard_block_only=True)
    if hard_blocks:
        return hard_blocks[0]

    triggered = _explanations(evaluation, hard_block_only=False)
    if not triggered:
        return None
    return "; ".join(triggered[:3])


def build_backend_block_reason(evaluation: Optional[Dict[str, Any]]) -> str:
    detail = _detail_from_evaluation(evaluation)
    if detail:
        return f"{BLOCK_SUMMARY}\n\nReason: {detail}"
    return BLOCK_SUMMARY


def decision_reason(decision: Decision) -> str:
    if decision == Decision.BLOCK:
        return BLOCK_SUMMARY
    if decision == Decision.WARN:
        return "AgentGuard marked the request as warn and allowed it to continue."
    return "AgentGuard approved the request."


def backend_failure_reason(source: str) -> str:
    if source == "backend_error":
        return _INVALID_RESPONSE_SUMMARY
    return FAIL_CLOSED_SUMMARY


def specific_block_reason(reason: str) -> str:
    """Strip the `BLOCK_SUMMARY` boilerplate so an interstitial shows only the
    specific cause. Falls back to the raw text when there is nothing to strip."""
    raw = (reason or "").strip()
    if _REASON_MARKER in raw:
        return raw.split(_REASON_MARKER, 1)[1].strip()
    if raw.startswith(BLOCK_SUMMARY):
        return raw[len(BLOCK_SUMMARY):].strip() or raw
    return raw
