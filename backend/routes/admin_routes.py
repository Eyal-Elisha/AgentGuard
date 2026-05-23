"""Admin routes for global statistics."""

from __future__ import annotations

from flask import jsonify

from ..auth import request_is_admin, require_jwt
from ..storage.db import _connect
from . import app_bp


@app_bp.route("/admin/stats", methods=["GET"])
@require_jwt
def admin_stats():
    if not request_is_admin():
        return jsonify({"error": "Forbidden"}), 403

    with _connect() as conn:
        total_sessions = conn.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"]
        total_events = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"]
        total_users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]

    return jsonify({
        "total_sessions": int(total_sessions),
        "total_events": int(total_events),
        "total_users": int(total_users),
    }), 200
