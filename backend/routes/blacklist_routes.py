from __future__ import annotations

from flask import jsonify, request

from backend.auth import require_admin
from backend.custom_blacklist import write_custom_blacklist_file
from backend.proxy.rule_engine import get_custom_blacklist, reload_custom_blacklist
from . import app_bp


@app_bp.route("/blacklist", methods=["GET"])
@require_admin
def get_blacklist():
    entries = sorted(get_custom_blacklist())
    return jsonify({"entries": entries}), 200


@app_bp.route("/blacklist", methods=["PUT"])
@require_admin
def update_blacklist():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON request body is required"}), 400

    try:
        normalized = write_custom_blacklist_file(payload.get("entries"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except OSError as exc:
        return jsonify({"error": f"Failed to update blacklist: {exc}"}), 500

    reload_custom_blacklist(normalized)
    return jsonify({
        "message": "Blacklist updated successfully",
        "entries": sorted(normalized),
    }), 200
