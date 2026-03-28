"""Authentication endpoints."""

from __future__ import annotations

from flask import jsonify, request

from ..auth import hash_password, issue_token, verify_password
from ..storage import sqlite_store as store
from ..validation import validate_login_signup
from . import app_bp


@app_bp.route("/login", methods=["POST"])
def login():
    payload, err = validate_login_signup(request.get_json(silent=True))
    if err:
        return jsonify({"error": err}), 400
    user = store.user_get_by_username(payload["username"])
    if not user or not verify_password(user["password_hash"], payload["password"]):
        return jsonify({"error": "Invalid credentials"}), 401
    token = issue_token(user["user_id"], user["username"], bool(user["is_admin"]))
    return jsonify({"jwt": token}), 200


@app_bp.route("/signup", methods=["POST"])
def signup():
    payload, err = validate_login_signup(request.get_json(silent=True))
    if err:
        return jsonify({"error": err}), 400
    if store.user_get_by_username(payload["username"]):
        return jsonify({"error": "Username already exists"}), 400
    uid = store.user_create(payload["username"], hash_password(payload["password"]), is_admin=False)
    return jsonify({"message": "User created successfully", "user_id": uid}), 201
