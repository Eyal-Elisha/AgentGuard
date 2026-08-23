"""Persists one decision: the event row, one row per rule, and a journal line.
Rules that never ran keep a NULL score, which is what keeps a stored event
replayable.
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
            # Whether this rule hard-blocked *this request*, not whether it is
            # capable of hard-blocking. Storing the capability set the column on
            # every event for every hard-block rule, so the dashboard reported a
            # hard block on pages where nothing fired at all.
            hard_block=bool(rule_result.hard_block and rule_result.triggered),
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
    """'allow' -> 'Allow', the capitalisation the events table stores."""
    return decision.value.title()


def _ensure_rule_registered(rule_result: RuleResult) -> None:
    """Insert the rule into the `rules` table, or refresh it if it drifted.

    Analyses reference rules by code, so a rule the seeder never saw (a locally
    added one, say) still needs a row before its analysis can be written.

    Existing rows are re-synced rather than left alone. They used to be written
    once and never revisited, so a recalibrated weight or a rule demoted from
    hard-blocking left the database describing an engine that no longer exists,
    and the dashboard faithfully displayed the old values.
    """
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
    trimmed = description[:_MAX_DESCRIPTION_LENGTH] if description else None
    if store.rule_get(rule_result.rule_id):
        store.rule_sync_metadata(
            rule_code=rule_result.rule_id,
            weight=RULE_WEIGHTS.get(rule_result.rule_id, 0.0),
            rule_type=rule_type,
            compute_class=compute_class,
            description=trimmed,
        )
        return

    store.rule_create(
        rule_code=rule_result.rule_id,
        weight=RULE_WEIGHTS.get(rule_result.rule_id, 0.0),
        rule_type=rule_type,
        compute_class=compute_class,
        is_enabled=rule_result.rule_id not in CODE_DISABLED_RULES,
        is_hard_block=rule_result.hard_block,
        description=trimmed,
    )
