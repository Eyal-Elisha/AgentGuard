"""Policy decisions derived from a session risk score."""

from __future__ import annotations

from .constants import HIGH_RISK_LIMIT, LOW_RISK_LIMIT, MEDIUM_RISK_LIMIT


def risk_level(score: float) -> str:
    if score >= HIGH_RISK_LIMIT:
        return "critical"
    if score >= MEDIUM_RISK_LIMIT:
        return "high"
    if score >= LOW_RISK_LIMIT:
        return "medium"
    return "low"


def stop_reason(
    *,
    score: float,
    block_count: int,
    hard_block_count: int,
) -> str | None:
    if score >= HIGH_RISK_LIMIT:
        return "The combined session risk score reached the critical threshold."
    return None
