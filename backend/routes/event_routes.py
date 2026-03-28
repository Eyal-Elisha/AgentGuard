"""Global event endpoints."""

from __future__ import annotations

from flask import jsonify, request

from ..auth import require_jwt
from ..serializers import event_to_dict
from ..storage import sqlite_store as store
from ..validation import parse_event_filters
from . import app_bp


@app_bp.route("/events", methods=["GET"])
@require_jwt
def list_all_events():
    filters, err = parse_event_filters(request.args)
    if err:
        return jsonify({"error": err}), 400
    rows = store.events_list_all(filters)
    return jsonify([event_to_dict(e, include_session=True) for e in rows]), 200


@app_bp.route("/events/<int:event_id>", methods=["GET"])
@require_jwt
def get_event(event_id: int):
    ev = store.event_get(event_id)
    if not ev:
        return jsonify({"error": "Event not found"}), 404
    return jsonify(event_to_dict(ev, include_session=True)), 200
