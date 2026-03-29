"""Rules and rule analysis endpoints."""

from __future__ import annotations

from flask import jsonify, request

from ..auth import require_jwt
from ..serializers import analysis_to_dict, rule_to_dict
from ..storage import sqlite_store as store
from ..validation import (
    validate_rule_payload,
    validate_rules_analysis_list_query,
    validate_rules_analysis_payload,
)
from . import app_bp


@app_bp.route("/rules", methods=["GET"])
@require_jwt
def list_rules():
    rows = store.rules_list_asc()
    return jsonify([rule_to_dict(r) for r in rows]), 200


@app_bp.route("/rules/<string:rule_code>", methods=["GET"])
@require_jwt
def get_rule(rule_code: str):
    r = store.rule_get(rule_code)
    if not r:
        return jsonify({"error": "Rule not found"}), 404
    return jsonify(rule_to_dict(r)), 200


@app_bp.route("/rules", methods=["POST"])
@require_jwt
def create_rule():
    data, err = validate_rule_payload(request.get_json(silent=True), partial=False)
    if err:
        return jsonify({"error": err}), 400
    if store.rule_get(data["rule_code"]):
        return jsonify({"error": "rule_code already exists"}), 409
    store.rule_create(
        data["rule_code"],
        data["weight"],
        data["rule_type"],
        data["compute_class"],
        data["is_enabled"],
        data["is_hard_block"],
        data.get("description"),
    )
    created_rule = store.rule_get(data["rule_code"])
    if created_rule is None:
        return jsonify({"error": "Failed to load created rule"}), 500
    return jsonify({"message": "Rule created successfully", "rule": rule_to_dict(created_rule)}), 201


@app_bp.route("/events/<int:event_id>/rules-analysis", methods=["GET"])
@require_jwt
def list_event_rules_analysis(event_id: int):
    if not store.event_get(event_id):
        return jsonify({"error": "Event not found"}), 404
    rows = store.rule_analysis_list_for_event(event_id)
    return jsonify([analysis_to_dict(a) for a in rows]), 200


@app_bp.route("/rules-analysis", methods=["POST"])
@require_jwt
def create_rules_analysis():
    data, err = validate_rules_analysis_payload(request.get_json(silent=True))
    if err:
        return jsonify({"error": err}), 400
    if not store.event_get(data["event_id"]):
        return jsonify({"error": "Referenced event does not exist"}), 404
    if not store.rule_get(data["rule_code"]):
        return jsonify({"error": "Referenced rule does not exist"}), 404
    aid = store.rule_analysis_create(
        data["event_id"],
        data["rule_code"],
        data["rule_score"],
        data["details"],
    )
    return jsonify({"message": "Rule analysis created successfully", "analysis_id": aid}), 201


@app_bp.route("/rules-analysis", methods=["GET"])
@require_jwt
def list_rules_analysis():
    query, err = validate_rules_analysis_list_query(
        request.args.get("rule_code"),
        request.args.get("limit", "100"),
    )
    if err:
        return jsonify({"error": err}), 400
    if not store.rule_get(query["rule_code"]):
        return jsonify({"error": "Rule not found"}), 404
    rows = store.rule_analysis_list_for_rule(query["rule_code"], query["limit"])
    return jsonify([analysis_to_dict(a) for a in rows]), 200
