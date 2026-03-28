"""Session and session-scoped event endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from flask import jsonify, request

from ..auth import get_optional_auth_payload, require_jwt
from ..serializers import event_to_dict, session_to_dict
from ..storage import sqlite_store as store
from ..validation import (
    parse_event_filters,
    validate_create_session,
    validate_event_payload,
    validate_update_session,
)
from . import app_bp


def _optional_user_id() -> int | None:
    payload, err = get_optional_auth_payload(request)
    if err:
        raise ValueError(err)
    if payload is None:
        return None
    return int(payload["sub"])


def _get_session_or_404(session_id: int):
    session = store.session_get(session_id)
    if session is None:
        return None, (jsonify({"error": "Session not found"}), 404)
    return session, None


@app_bp.route("/sessions", methods=["GET"])
@require_jwt
def list_sessions():
    rows = store.sessions_list_desc()
    return jsonify([session_to_dict(s) for s in rows]), 200


@app_bp.route("/sessions", methods=["POST"])
@require_jwt
def create_session():
    data, err = validate_create_session(request.get_json(silent=True))
    if err:
        return jsonify({"error": err}), 400
    try:
        uid = _optional_user_id()
    except ValueError:
        return jsonify({"error": "Unauthorized"}), 401
    sid = store.session_create(uid, data["start_time"], data["environment"], data["agent_name"])
    return (
        jsonify(
            {
                "message": "Session created successfully",
                "session_id": sid,
            }
        ),
        201,
    )


@app_bp.route("/sessions/<int:session_id>", methods=["GET"])
@require_jwt
def get_session(session_id: int):
    sess, not_found = _get_session_or_404(session_id)
    if not_found:
        return not_found
    return jsonify(session_to_dict(sess)), 200


@app_bp.route("/sessions/<int:session_id>", methods=["PUT"])
@require_jwt
def update_session(session_id: int):
    sess, not_found = _get_session_or_404(session_id)
    if not_found:
        return not_found
    data, err = validate_update_session(request.get_json(silent=True))
    if err:
        return jsonify({"error": err}), 400
    store.session_update_end(session_id, data["end_time"])
    return jsonify({"message": "Session updated successfully"}), 200


@app_bp.route("/sessions/<int:session_id>", methods=["DELETE"])
@require_jwt
def delete_session(session_id: int):
    if not store.session_delete(session_id):
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"message": "Session deleted successfully"}), 200


@app_bp.route("/sessions/<int:session_id>/close", methods=["POST"])
@require_jwt
def close_session(session_id: int):
    result = store.session_try_close(session_id, datetime.now(timezone.utc))
    if result == "not_found":
        return jsonify({"error": "Session not found"}), 404
    if result == "already_closed":
        return jsonify({"error": "Session is already closed"}), 409
    return jsonify({"message": "Session closed successfully"}), 200


@app_bp.route("/sessions/<int:session_id>/events/stats", methods=["GET"])
@require_jwt
def session_event_stats(session_id: int):
    stats = store.session_stats(session_id)
    if stats is None:
        return jsonify({"error": "Session not found"}), 404
    return (
        jsonify(
            {
                "session_id": session_id,
                "total_events": stats["total_events"],
                "allow": stats["allow"],
                "warn": stats["warn"],
                "block": stats["block"],
                "average_risk_score": stats["average_risk_score"],
            }
        ),
        200,
    )


@app_bp.route("/sessions/<int:session_id>/events", methods=["POST"])
@require_jwt
def create_session_event(session_id: int):
    _, not_found = _get_session_or_404(session_id)
    if not_found:
        return not_found
    data, err = validate_event_payload(request.get_json(silent=True))
    if err:
        return jsonify({"error": err}), 400
    eid = store.event_create(
        session_id,
        data["timestamp"],
        data["url"],
        data["guard_action"],
        data["risk_score"],
        data["method"],
        json.dumps(data["headers"]),
    )
    return jsonify({"message": "Event created successfully", "event_id": eid}), 201


@app_bp.route("/sessions/<int:session_id>/events", methods=["GET"])
@require_jwt
def list_session_events(session_id: int):
    _, not_found = _get_session_or_404(session_id)
    if not_found:
        return not_found
    filters, err = parse_event_filters(request.args)
    if err:
        return jsonify({"error": err}), 400
    rows = store.events_list_for_session(session_id, filters, order="ASC")
    return jsonify([event_to_dict(e, include_session=False) for e in rows]), 200
