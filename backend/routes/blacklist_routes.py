from __future__ import annotations

from typing import Any
from flask import Blueprint, jsonify, request

from backend.auth import require_jwt
from backend.custom_blacklist import custom_blacklist_file_path, parse_custom_blacklist_file_content
from backend.proxy.rule_engine import get_custom_blacklist, reload_custom_blacklist
from . import api_bp


@api_bp.route("/blacklist", methods=["GET"])
@require_jwt
def get_blacklist():
    entries = sorted(list(get_custom_blacklist()))
    return jsonify({"entries": entries}), 200


@api_bp.route("/blacklist", methods=["PUT", "OPTIONS"])
@require_jwt
def update_blacklist():
    if request.method == "OPTIONS":
        return "", 204

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON request body is required"}), 400

    entries = payload.get("entries")
    if not isinstance(entries, list):
        return jsonify({"error": "'entries' must be a list of strings"}), 400

    # Ensure all entries are strings
    entries = [str(e).strip().lower() for e in entries if isinstance(e, str) and e.strip()]
    
    # Save to file
    content = "# AgentGuard custom blacklist — one hostname or full URL per line.\n"
    content += "# This file is the custom blacklist policy source for the proxy and Stage A rule 9.\n"
    content += "\n".join(entries) + "\n"

    try:
        path = custom_blacklist_file_path()
        path.write_text(content, encoding="utf-8")
        
        # Reload into proxy memory
        reloaded_frozenset = parse_custom_blacklist_file_content(content)
        reload_custom_blacklist(reloaded_frozenset)
        
        return jsonify({
            "message": "Blacklist updated successfully",
            "entries": sorted(list(reloaded_frozenset))
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update blacklist: {e}"}), 500
