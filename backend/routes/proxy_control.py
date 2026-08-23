"""Start, stop and observe the local proxies from the dashboard. Every route
here addresses one agent: starting opens a proxy session for it and stopping
closes one, and neither touches another agent's instance. Passive mode is the
exception, and is deliberately system-wide: all instances call the one backend.
"""

from __future__ import annotations

from flask import g, jsonify, request

from backend.auth import require_jwt
from backend.proxy.audit import (
    close_proxy_session,
    ensure_proxy_session_started,
    is_catalogue_agent,
    normalize_proxy_agent_name,
)
from backend.proxy.launcher.browser import is_launchable, launch_browser
from backend.proxy.ports import ports_for_agent
from backend.settings import get_passive_mode, set_passive_mode
from backend.storage import sqlite_store as store
from backend.validation.proxy_decision import parse_agent_name, parse_environment

from . import api_bp
from .guards import local_clients_only

from backend.proxy.launcher import (
    any_proxy_running,
    proxy_is_running,
    proxy_status_snapshot,
    start_proxy_process,
    stop_proxy_process,
)


@api_bp.route("/proxy/status", methods=["GET"])
@require_jwt
@local_clients_only
def proxy_status():
    """One entry per agent, plus `active` for whether any of them is running."""
    return jsonify({"active": any_proxy_running(), "agents": proxy_status_snapshot()}), 200


@api_bp.route("/proxy/control", methods=["POST", "OPTIONS"])
@require_jwt
@local_clients_only
def proxy_control():
    """Start or stop one agent's mitmweb, and its session."""
    if request.method == "OPTIONS":
        return "", 204
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
    # Only a catalogue agent has ports allocated to it, so only a catalogue
    # agent can be launched, however the name is spelled on the way in.
    if not is_catalogue_agent(agent_name):
        return jsonify({"error": f"Unknown agent: {agent_name}"}), 400

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
        ok, message = stop_proxy_process(agent_name=agent_name)
        session = close_proxy_session(environment=environment, agent_name=agent_name) if ok else None

    running = proxy_is_running(agent_name)
    if not ok:
        return jsonify({"error": message, "active": running, "agent_name": agent_name}), 500

    ports = ports_for_agent(agent_name)
    response = {
        "active": running,
        "message": message,
        "agent_name": agent_name,
        "proxy_port": ports.listen_port,
        "admin_port": ports.web_port,
    }
    # A named agent only reaches its proxy by being launched at that port, so
    # protecting one opens it. Failing to is reported, not raised.
    if active and running and is_launchable(agent_name):
        launched, detail = launch_browser(agent_name)
        response["browser_launched"] = launched
        if not launched:
            response["browser_error"] = detail
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
