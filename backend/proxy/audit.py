from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from backend.analysis.rules import (
    DETERMINISTIC_RULES,
    RULE_WEIGHTS,
    ComputeClass,
    Decision,
    EvaluationResult,
    RuleType,
)
from backend.audit_logging import configure_audit_logger
from backend.storage import sqlite_store as store

_logger = logging.getLogger("agentguard.audit")
_RULE_DEFINITIONS = {rule.rule_id: rule for rule in DETERMINISTIC_RULES}
_DEFAULT_PROXY_AGENT_NAME = "browserOS"
_DEFAULT_PROXY_ENVIRONMENT = "prod"


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_storage_ready() -> None:
    store.init_schema()


def _get_audit_logger() -> logging.Logger:
    if _logger.handlers:
        return _logger
    return configure_audit_logger()


def _log_audit_record(record: dict[str, Any]) -> None:
    _get_audit_logger().info(json.dumps(record, sort_keys=True))


def _clean_agent_name(value: str) -> str:
    cleaned = "".join(ch for ch in value.strip() if ch.isalnum() or ch in "._ -")
    if not cleaned:
        return _DEFAULT_PROXY_AGENT_NAME
    return cleaned[:20]


def normalize_proxy_agent_name(explicit_agent_name: str | None) -> str:
    if isinstance(explicit_agent_name, str) and explicit_agent_name.strip():
        return _clean_agent_name(explicit_agent_name)
    return _DEFAULT_PROXY_AGENT_NAME


def _resolve_agent_name(explicit_agent_name: str | None) -> str:
    return normalize_proxy_agent_name(explicit_agent_name)


def _guard_action(decision: Decision) -> str:
    return decision.value.title()


def _ensure_rule_registered(rule_result) -> None:
    if store.rule_get(rule_result.rule_id):
        return

    rule_definition = _RULE_DEFINITIONS.get(rule_result.rule_id)
    description = rule_definition.description if rule_definition is not None else rule_result.explanation
    compute_class = (
        rule_definition.compute_class.value
        if rule_definition is not None
        else ComputeClass.CHEAP.value
    )
    store.rule_create(
        rule_code=rule_result.rule_id,
        weight=RULE_WEIGHTS.get(rule_result.rule_id, 0.0),
        rule_type=rule_result.rule_type.value if isinstance(rule_result.rule_type, RuleType) else str(rule_result.rule_type),
        compute_class=compute_class,
        is_enabled=True,
        is_hard_block=rule_result.hard_block,
        description=description[:255] if description else None,
    )


def _resolve_session_id(
    *,
    session_id: int | None,
    timestamp: datetime,
    environment: str,
    agent_name: str,
) -> int:
    _ensure_storage_ready()

    if session_id is not None:
        session = store.session_get(session_id)
        if session is not None:
            session_environment = str(session["environment"])
            session_agent_name = str(session["agent_name"])
            if session_environment != environment:
                raise ValueError("Provided environment does not match the referenced session")
            if session_agent_name != agent_name:
                raise ValueError("Provided agent_name does not match the referenced session")
            return int(session["session_id"])
        raise ValueError("Provided session_id does not reference an existing session")

    existing_session = store.session_get_latest_open_by_agent(agent_name, environment)
    if existing_session is not None:
        return int(existing_session["session_id"])

    return store.session_create(
        user_id=None,
        start_time=timestamp,
        environment=environment,
        agent_name=agent_name,
    )


def ensure_proxy_session_started(
    *,
    timestamp: datetime | None = None,
    environment: str = _DEFAULT_PROXY_ENVIRONMENT,
    agent_name: str = _DEFAULT_PROXY_AGENT_NAME,
) -> dict[str, Any]:
    _ensure_storage_ready()

    started_at = timestamp or datetime.now(timezone.utc)
    resolved_agent_name = _resolve_agent_name(agent_name)
    existing_session = store.session_get_latest_open_by_agent(resolved_agent_name, environment)
    replaced_session_id: int | None = None
    if existing_session is not None:
        replaced_session_id = int(existing_session["session_id"])
        store.session_try_close(replaced_session_id, started_at)
        _log_audit_record(
            {
                "timestamp": _iso_z(started_at),
                "agent": resolved_agent_name,
                "environment": environment,
                "session_id": replaced_session_id,
                "event": "proxy_session_closed",
                "reason": "superseded_by_new_proxy_session",
            }
        )

    session_id = store.session_create(
        user_id=None,
        start_time=started_at,
        environment=environment,
        agent_name=resolved_agent_name,
    )
    started_record = {
        "timestamp": _iso_z(started_at),
        "agent": resolved_agent_name,
        "environment": environment,
        "session_id": session_id,
        "event": "proxy_session_started",
    }
    if replaced_session_id is not None:
        started_record["replaced_session_id"] = replaced_session_id
    _log_audit_record(started_record)
    response = {
        "session_id": session_id,
        "agent": resolved_agent_name,
        "environment": environment,
        "created": True,
    }
    if replaced_session_id is not None:
        response["replaced_session_id"] = replaced_session_id
    return response


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
    resolved_agent_name = _resolve_agent_name(agent_name)
    resolved_session_id = _resolve_session_id(
        session_id=session_id,
        timestamp=timestamp,
        environment=environment,
        agent_name=resolved_agent_name,
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

    persisted_rules = 0
    triggered_rules = 0
    for rule_result in evaluation.rule_results:
        _ensure_rule_registered(rule_result)
        store.rule_analysis_create(
            event_id=event_id,
            rule_code=rule_result.rule_id,
            rule_score=rule_result.score,
            details=rule_result.explanation,
        )
        persisted_rules += 1
        if rule_result.triggered:
            triggered_rules += 1

    record = {
        "timestamp": _iso_z(timestamp),
        "agent": resolved_agent_name,
        "environment": environment,
        "session_id": resolved_session_id,
        "event_id": event_id,
        "url": url,
        "method": method.upper(),
        "risk_score": float(evaluation.risk_score),
        "decision": evaluation.decision.value,
        "hard_block_triggered": evaluation.hard_block_triggered,
        "stage_b_required": evaluation.stage_b_required,
        "rule_count": persisted_rules,
        "triggered_rule_count": triggered_rules,
    }
    _log_audit_record(record)
    return record
