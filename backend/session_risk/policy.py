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
    sensitive_count: int,
    recent_weighted_risk: float,
) -> str | None:
    if hard_block_count > 0:
        return "A hard-block rule was triggered during this session."
    if block_count >= 2:
        return "Multiple requests were blocked during this session."
    if score >= HIGH_RISK_LIMIT:
        return "The combined session risk score reached the critical threshold."
    if sensitive_count >= 3 and recent_weighted_risk >= 0.60:
        return "Sensitive interactions repeated while recent risk stayed high."
    return None
