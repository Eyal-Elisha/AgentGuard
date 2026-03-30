from __future__ import annotations

from datetime import datetime, timezone
import ipaddress
from typing import Any

from flask import jsonify, request

from backend.proxy.audit import (
    close_proxy_session,
    ensure_proxy_session_started,
    normalize_proxy_agent_name,
    record_proxy_decision,
)
from backend.proxy.rule_engine import evaluate_http_payload
from backend.proxy.utils import evaluation_result_to_dict
from backend.storage import sqlite_store as store
from backend.validation.common import ALLOWED_ENVIRONMENTS, parse_iso_datetime, parse_positive_int

from . import api_bp

try:
    from proxy_launcher import (
        proxy_is_running,
        start_proxy_process,
        stop_proxy_process,
    )
except ImportError:  # pragma: no cover - alternate cwd
    proxy_is_running = None  # type: ignore[assignment, misc]
    start_proxy_process = None  # type: ignore[assignment, misc]
    stop_proxy_process = None  # type: ignore[assignment, misc]

_LOCALHOST_ADDRS = frozenset({"127.0.0.1", "::1"})


def _is_trusted_client(remote_addr: str | None) -> bool:
    """Allow localhost and RFC1918 private LAN clients (dev-friendly)."""
    if not remote_addr:
        return False
    if remote_addr in _LOCALHOST_ADDRS:
        return True
    try:
        ip = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False
    return ip.is_private


def _require_non_empty_string(payload: dict[str, Any], field: str) -> str | None:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _normalize_headers(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): str(item) for key, item in value.items()}


def _optional_clean_string(payload: dict[str, Any], field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _payload_timestamp(payload: dict[str, Any]) -> datetime | None:
    raw = payload.get("timestamp")
    if raw is None:
        return datetime.now(timezone.utc)
    return parse_iso_datetime(raw)


def _payload_environment(payload: dict[str, Any]) -> str | None:
    raw = payload.get("environment")
    if raw is None:
        return "prod"
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip().lower()
    if cleaned not in ALLOWED_ENVIRONMENTS:
        return None
    return cleaned


def _payload_session_id(payload: dict[str, Any]) -> int | None:
    if "session_id" not in payload or payload["session_id"] is None:
        return None
    return parse_positive_int(payload["session_id"])


def _proxy_control_environment(payload: dict[str, Any]) -> str:
    environment = _payload_environment(payload)
    if environment is None:
        raise ValueError("'environment' must be one of: prod, test")
    return environment


def _proxy_control_agent_name(payload: dict[str, Any]) -> str:
    raw_agent_name = payload.get("agent_name")
    if raw_agent_name is None:
        return normalize_proxy_agent_name(None)
    if not isinstance(raw_agent_name, str) or not raw_agent_name.strip():
        raise ValueError("'agent_name' must be a non-empty string when provided")
    return normalize_proxy_agent_name(raw_agent_name)


@api_bp.route("/proxy/decision", methods=["POST"])
def proxy_decision():
    if not _is_trusted_client(request.remote_addr):
        return jsonify({"error": "This endpoint is only available from a trusted local network client"}), 403

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON request body is required"}), 400

    required_fields = ("url", "method", "headers", "body")
    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    url = _require_non_empty_string(payload, "url")
    if url is None:
        return jsonify({"error": "'url' must be a non-empty string"}), 400

    method = _require_non_empty_string(payload, "method")
    if method is None:
        return jsonify({"error": "'method' must be a non-empty string"}), 400

    headers = _normalize_headers(payload["headers"])
    if headers is None:
        return jsonify({"error": "'headers' must be an object"}), 400

    timestamp = _payload_timestamp(payload)
    if timestamp is None:
        return jsonify({"error": "'timestamp' must be a valid ISO-8601 datetime"}), 400

    environment = _payload_environment(payload)
    if environment is None:
        return jsonify({"error": "'environment' must be one of: prod, test"}), 400
    environment_was_provided = payload.get("environment") is not None

    session_id = _payload_session_id(payload)
    if "session_id" in payload and payload["session_id"] is not None and session_id is None:
        return jsonify({"error": "'session_id' must be a positive integer"}), 400

    agent_name = _optional_clean_string(payload, "agent_name")
    if "agent_name" in payload and payload["agent_name"] is not None and agent_name is None:
        return jsonify({"error": "'agent_name' must be a non-empty string when provided"}), 400
    agent_name_was_provided = payload.get("agent_name") is not None

    if session_id is not None:
        session = store.session_get(session_id)
        if session is None:
            return jsonify({"error": "Provided session_id does not reference an existing session"}), 400
        if session.get("end_time") is not None:
            return jsonify({"error": "Provided session_id is already closed"}), 400
        session_environment = str(session["environment"])
        session_agent_name = str(session["agent_name"])
        if environment_was_provided and session_environment != environment:
            return jsonify({"error": "Provided environment does not match the referenced session"}), 400
        if agent_name_was_provided and normalize_proxy_agent_name(agent_name) != session_agent_name:
            return jsonify({"error": "Provided agent_name does not match the referenced session"}), 400
        environment = session_environment
        agent_name = session_agent_name

    body = payload["body"]
    if isinstance(body, str):
        body = body.encode("utf-8", errors="replace")
    elif body is None:
        body = b""
    elif not isinstance(body, bytes):
        body = str(body).encode("utf-8", errors="replace")

    result = evaluate_http_payload(
        url=url,
        method=method.upper(),
        headers=headers,
        body=body,
    )
    try:
        audit_record = record_proxy_decision(
            timestamp=timestamp,
            url=url,
            method=method,
            headers=headers,
            evaluation=result,
            environment=environment,
            agent_name=agent_name,
            session_id=session_id,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(
        {
            "decision": result.decision.value,
            "evaluation": evaluation_result_to_dict(result),
            "audit": audit_record,
        }
    ), 200


@api_bp.route("/proxy/status", methods=["GET"])
def proxy_status():
    if not _is_trusted_client(request.remote_addr):
        return jsonify({"error": "This endpoint is only available from a trusted local network client"}), 403
    if proxy_is_running is None:
        return jsonify({"error": "Proxy launcher is not available on this server"}), 503
    return jsonify({"active": proxy_is_running()}), 200


@api_bp.route("/proxy/control", methods=["POST", "OPTIONS"])
def proxy_control():
    """Start or stop mitmweb with `traffic_interception.py` (same as `python proxy_launcher.py`)."""
    if request.method == "OPTIONS":
        return "", 204
    if not _is_trusted_client(request.remote_addr):
        return jsonify({"error": "This endpoint is only available from a trusted local network client"}), 403
    if start_proxy_process is None or stop_proxy_process is None:
        return jsonify({"error": "Proxy launcher is not available on this server"}), 503

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON request body is required"}), 400
    active = payload.get("active")
    if not isinstance(active, bool):
        return jsonify({"error": "'active' must be a boolean"}), 400
    try:
        environment = _proxy_control_environment(payload)
        agent_name = _proxy_control_agent_name(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if active:
        ok, message = start_proxy_process()
        session = None
        if ok and message != "already_running":
            session = ensure_proxy_session_started(environment=environment, agent_name=agent_name)
    else:
        ok, message = stop_proxy_process()
        session = None
        if ok:
            session = close_proxy_session(environment=environment, agent_name=agent_name)

    running = proxy_is_running()
    if not ok:
        return jsonify({"error": message, "active": running}), 500
    response = {"active": running, "message": message}
    if session is not None:
        response["session"] = session
    return jsonify(response), 200
