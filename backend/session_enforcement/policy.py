"""Policy mapping from session risk to enforcement actions."""

from __future__ import annotations

from backend.analysis.rules import Decision
from backend.session_risk.constants import HIGH_RISK_LIMIT, LOW_RISK_LIMIT, MEDIUM_RISK_LIMIT


def stronger_decision(current: Decision, candidate: Decision) -> Decision:
    rank = {
        Decision.ALLOW: 0,
        Decision.WARN: 1,
        Decision.BLOCK: 2,
    }
    return candidate if rank[candidate] > rank[current] else current


def enforcement_level(score: float) -> str:
    if score >= HIGH_RISK_LIMIT:
        return "stop"
    if score >= MEDIUM_RISK_LIMIT:
        return "confirm"
    if score >= LOW_RISK_LIMIT:
        return "warn"
    return "allow"


def level_decision(level: str) -> Decision:
    if level == "stop":
        return Decision.WARN
    if level in {"confirm", "warn"}:
        return Decision.WARN
    return Decision.ALLOW


def level_reason(level: str, score: float) -> str | None:
    if level == "stop":
        return f"Session stopped for review; risk score is {score:.2f}."
    if level == "confirm":
        return f"Session needs user confirmation; risk score is {score:.2f}."
    if level == "warn":
        return f"Session risk is elevated; risk score is {score:.2f}."
    return None
