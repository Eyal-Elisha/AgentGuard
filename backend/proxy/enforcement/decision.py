"""`BackendDecision` — the verdict the proxy acts on, and how one is built.

Every path through the addon ends up holding one of these, whether it came
from the backend, from a rule the proxy applied locally, or from the backend
being unreachable. `source` records which, because the enforcement response
differs: a real block is a 403, an unavailable backend is a 503.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from backend.analysis.rules import Decision
from backend.settings import BackendFailureMode, get_backend_failure_mode

from .reasons import BLOCK_SUMMARY

#: `source` values meaning "we never got an answer from the backend".
BACKEND_FAILURE_SOURCES = frozenset({"backend_timeout", "backend_unreachable", "backend_error"})


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


def local_rule_block_decision(*, rule_id: str, explanation: str, source: str) -> BackendDecision:
    """A block the proxy decided by itself, without calling the backend.

    The synthetic evaluation mirrors the shape the backend would have returned
    so the interstitial and the audit log can render it the same way.
    """
    return BackendDecision(
        decision=Decision.BLOCK,
        reason=f"{BLOCK_SUMMARY}\n\nReason: {explanation}",
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


def failure_decision(*, source: str, reason: str) -> BackendDecision:
    """What to do when the backend could not be consulted.

    Fail-closed (the default) blocks; fail-open lets the request through. The
    mode is read per call so a change in `backend/.env` takes effect without
    restarting the proxy.
    """
    if get_backend_failure_mode() == BackendFailureMode.FAIL_OPEN:
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
