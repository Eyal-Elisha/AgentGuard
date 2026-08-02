"""Persisting one decision: the event row, one row per rule, and a journal line.

Every rule the engine considered is written out, including the ones that never
ran — those keep a NULL score. That is what makes a stored event replayable:
you can tell "this rule found nothing" from "this rule was skipped".
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from backend.analysis.rules import (
    CODE_DISABLED_RULES,
    RULE_WEIGHTS,
    RULES_BY_ID,
    ComputeClass,
    Decision,
    EvaluationResult,
    RuleResult,
    RuleType,
)
from backend.storage import sqlite_store as store

from .agents import normalize_proxy_agent_name
from .journal import iso_z, log_record
from .sessions import resolve_proxy_session_id

_MAX_DESCRIPTION_LENGTH = 255


def record_proxy_decision(
    *,
    timestamp: datetime,
    url: str,
    method: str,
    headers: dict[str, str],
    evaluation: EvaluationResult,
    environment: str,
    agent_name: str | None = None,
    session_id: int | None = None,
) -> dict[str, Any]:
    """Store the decision and return the record written to the journal."""
    agent = normalize_proxy_agent_name(agent_name)
    resolved_session_id = resolve_proxy_session_id(
        session_id=session_id,
        timestamp=timestamp,
        environment=environment,
        agent_name=agent,
    )

    event_id = store.event_create(
        session_id=resolved_session_id,
        timestamp=timestamp,
        url=url,
        guard_action=_guard_action(evaluation.decision),
        risk_score=float(evaluation.risk_score),
        http_method=method.upper(),
        headers_json=json.dumps(headers, sort_keys=True),
    )

    for rule_result in evaluation.rule_results:
        _ensure_rule_registered(rule_result)
        store.rule_analysis_create(
            event_id=event_id,
            rule_code=rule_result.rule_id,
            rule_score=rule_result.score,
            details=rule_result.explanation,
            hard_block=rule_result.hard_block,
        )

    record = {
        "timestamp": iso_z(timestamp),
        "agent": agent,
        "environment": environment,
        "session_id": resolved_session_id,
        "event_id": event_id,
        "url": url,
        "method": method.upper(),
        "risk_score": float(evaluation.risk_score),
        "decision": evaluation.decision.value,
        "hard_block_triggered": evaluation.hard_block_triggered,
        "stage_b_required": evaluation.stage_b_required,
        "rule_count": len(evaluation.rule_results),
        "triggered_rule_count": sum(1 for r in evaluation.rule_results if r.triggered),
    }
    log_record(record)
    return record


def _guard_action(decision: Decision) -> str:
    """'allow' -> 'Allow' — the capitalisation the `events` table stores."""
    return decision.value.title()


def _ensure_rule_registered(rule_result: RuleResult) -> None:
    """Insert the rule into the `rules` table if this is the first time it ran.

    Analyses reference rules by code, so a rule the seeder never saw (a locally
    added one, say) still needs a row before its analysis can be written.
    """
    if store.rule_get(rule_result.rule_id):
        return

    definition = RULES_BY_ID.get(rule_result.rule_id)
    description = definition.description if definition is not None else rule_result.explanation
    compute_class = (
        definition.compute_class.value if definition is not None else ComputeClass.CHEAP.value
    )
    rule_type = (
        rule_result.rule_type.value
        if isinstance(rule_result.rule_type, RuleType)
        else str(rule_result.rule_type)
    )
    store.rule_create(
        rule_code=rule_result.rule_id,
        weight=RULE_WEIGHTS.get(rule_result.rule_id, 0.0),
        rule_type=rule_type,
        compute_class=compute_class,
        is_enabled=rule_result.rule_id not in CODE_DISABLED_RULES,
        is_hard_block=rule_result.hard_block,
        description=description[:_MAX_DESCRIPTION_LENGTH] if description else None,
    )
