"""Start, stop and observe the local proxy from the dashboard. Starting opens a
proxy session and stopping closes one; passive mode keeps evaluating but stops
enforcing.
"""

from __future__ import annotations

from flask import g, jsonify, request

from backend.auth import require_jwt
from backend.proxy.audit import (
    close_proxy_session,
    ensure_proxy_session_started,
    normalize_proxy_agent_name,
)
from backend.settings import get_passive_mode, set_passive_mode
from backend.storage import sqlite_store as store
from backend.validation.proxy_decision import parse_agent_name, parse_environment

from . import api_bp
from .guards import local_clients_only

try:
    from proxy_launcher import proxy_is_running, start_proxy_process, stop_proxy_process
except ImportError:  # pragma: no cover - the launcher is not importable from every cwd
    proxy_is_running = None  # type: ignore[assignment, misc]
    start_proxy_process = None  # type: ignore[assignment, misc]
    stop_proxy_process = None  # type: ignore[assignment, misc]

_LAUNCHER_UNAVAILABLE = "Proxy launcher is not available on this server"


@api_bp.route("/proxy/status", methods=["GET"])
@require_jwt
@local_clients_only
def proxy_status():
    if proxy_is_running is None:
        return jsonify({"error": _LAUNCHER_UNAVAILABLE}), 503
    return jsonify({"active": proxy_is_running()}), 200


@api_bp.route("/proxy/control", methods=["POST", "OPTIONS"])
@require_jwt
@local_clients_only
def proxy_control():
    """Start or stop mitmweb with `traffic_interception.py`, and its session."""
    if request.method == "OPTIONS":
        return "", 204
    if start_proxy_process is None or stop_proxy_process is None:
        return jsonify({"error": _LAUNCHER_UNAVAILABLE}), 503

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON request body is required"}), 400
    active = payload.get("active")
    if not isinstance(active, bool):
        return jsonify({"error": "'active' must be a boolean"}), 400
    try:
        environment = parse_environment(payload)
        agent_name = normalize_proxy_agent_name(parse_agent_name(payload))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if active:
        ok, message = start_proxy_process(agent_name=agent_name, environment=environment)
        # "already_running" means an earlier call opened the session already.
        session = (
            ensure_proxy_session_started(
                environment=environment, agent_name=agent_name, user_id=_session_user_id()
            )
            if ok and message != "already_running"
            else None
        )
    else:
        ok, message = stop_proxy_process()
        session = close_proxy_session(environment=environment, agent_name=agent_name) if ok else None

    running = proxy_is_running()
    if not ok:
        return jsonify({"error": message, "active": running}), 500

    response = {"active": running, "message": message}
    if session is not None:
        response["session"] = session
    return jsonify(response), 200


@api_bp.route("/proxy/passive-mode", methods=["GET"])
@require_jwt
@local_clients_only
def get_passive_mode_route():
    return jsonify({"passive_mode": get_passive_mode()}), 200


@api_bp.route("/proxy/passive-mode", methods=["PATCH", "OPTIONS"])
@require_jwt
@local_clients_only
def set_passive_mode_route():
    if request.method == "OPTIONS":
        return "", 204
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON request body is required"}), 400
    value = payload.get("passive_mode")
    if not isinstance(value, bool):
        return jsonify({"error": "'passive_mode' must be a boolean"}), 400
    set_passive_mode(value)
    return jsonify({"passive_mode": get_passive_mode()}), 200


def _session_user_id() -> int | None:
    """The JWT user to attribute the session to, if it maps to a real row.

    Sessions carry a nullable user_id, so an unknown or absent user is left
    off rather than failing the request on a foreign-key error.
    """
    raw_user_id = getattr(g, "jwt_user_id", None)
    if raw_user_id is None:
        return None
    try:
        user_id = int(raw_user_id)
    except (TypeError, ValueError):
        return None
    if store.user_get(user_id) is None:
        return None
    return user_id
