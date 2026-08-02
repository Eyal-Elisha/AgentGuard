"""`POST /api/proxy/decision` — the endpoint the mitmproxy addon blocks on.

Every intercepted request that survives the proxy's filter chain arrives here,
and the proxy holds the connection open until it answers, so this is the one
route on the critical path of the user's browsing.

The proxy's start/stop controls live in `proxy_control.py`.
"""

from __future__ import annotations

import logging
import sqlite3

from flask import jsonify, request

from backend.proxy.audit import (
    normalize_proxy_agent_name,
    record_proxy_decision,
    resolve_proxy_session_id,
)
from backend.proxy.rule_engine import evaluate_http_payload
from backend.proxy.utils import evaluation_result_to_dict
from backend.settings import get_passive_mode
from backend.storage import sqlite_store as store
from backend.validation import validate_proxy_payload
from backend.validation.proxy_decision import DecisionRequest, parse_decision_request

from . import api_bp
from .guards import local_clients_only

_api_logger = logging.getLogger("agentguard.api")


@api_bp.route("/proxy/decision", methods=["POST"])
@local_clients_only
def proxy_decision():
    payload, validation_error, validation_status = validate_proxy_payload(
        request.get_json(silent=True)
    )
    if validation_error:
        return jsonify({"error": validation_error}), validation_status
    assert payload is not None

    try:
        decision_request = parse_decision_request(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        environment, agent_name = _attribute_to_session(decision_request)
        session_id = resolve_proxy_session_id(
            session_id=decision_request.session_id,
            timestamp=decision_request.timestamp,
            environment=environment,
            agent_name=normalize_proxy_agent_name(agent_name),
        )
        result = evaluate_http_payload(
            url=decision_request.url,
            method=decision_request.method,
            headers=decision_request.headers,
            body=decision_request.body,
            session_id=session_id,
            timestamp=decision_request.timestamp,
        )
        audit_record = record_proxy_decision(
            timestamp=decision_request.timestamp,
            url=decision_request.url,
            method=decision_request.method,
            headers=decision_request.headers,
            evaluation=result,
            environment=environment,
            agent_name=agent_name,
            session_id=session_id,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except sqlite3.OperationalError as exc:
        _api_logger.error("POST %s database error: %s", request.path, exc, exc_info=exc)
        return jsonify({"error": "Database temporarily unavailable"}), 503

    return jsonify(
        {
            "decision": result.decision.value,
            "evaluation": evaluation_result_to_dict(result),
            "audit": audit_record,
            "passive_mode": get_passive_mode(),
        }
    ), 200


def _attribute_to_session(decision_request: DecisionRequest) -> tuple[str, str | None]:
    """Settle which session, environment and agent this decision belongs to.

    With no explicit `session_id` the request is attributed to whatever session
    is currently open, and its own environment and agent name stand. With one,
    the session is authoritative: any environment or agent the proxy did send
    must agree with it, and anything it omitted is inherited.
    """
    if decision_request.session_id is None:
        return decision_request.environment, decision_request.agent_name

    session = store.session_get(decision_request.session_id)
    if session is None:
        raise ValueError("Provided session_id does not reference an existing session")
    if session.get("end_time") is not None:
        raise ValueError("Provided session_id is already closed")

    session_environment = str(session["environment"])
    session_agent_name = str(session["agent_name"])
    if decision_request.environment_was_provided and session_environment != decision_request.environment:
        raise ValueError("Provided environment does not match the referenced session")
    if (
        decision_request.agent_name_was_provided
        and normalize_proxy_agent_name(decision_request.agent_name) != session_agent_name
    ):
        raise ValueError("Provided agent_name does not match the referenced session")
    return session_environment, session_agent_name
