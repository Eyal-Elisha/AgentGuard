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

        avg_risk = conn.execute("SELECT AVG(risk_score) AS a FROM events").fetchone()["a"]
        global_avg_risk_score = float(avg_risk) if avg_risk is not None else 0.0

        allow = conn.execute("SELECT COUNT(*) AS c FROM events WHERE guard_action = 'Allow'").fetchone()["c"]
        warn = conn.execute("SELECT COUNT(*) AS c FROM events WHERE guard_action = 'Warn'").fetchone()["c"]
        block = conn.execute("SELECT COUNT(*) AS c FROM events WHERE guard_action = 'Block'").fetchone()["c"]

    return jsonify({
        "total_sessions": int(total_sessions),
        "total_events": int(total_events),
        "total_users": int(total_users),
        "global_avg_risk_score": global_avg_risk_score,
        "action_breakdown": {
            "Allow": int(allow),
            "Warn": int(warn),
            "Block": int(block),
        }
    }), 200
