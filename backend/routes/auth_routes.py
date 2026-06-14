"""Authentication endpoints."""

from __future__ import annotations

from flask import jsonify, request

from ..auth import hash_password, issue_token, request_is_admin, require_jwt, verify_password
from ..storage.sqlite_store import UsernameTakenError
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
    try:
        uid = store.user_create(
            payload["username"], hash_password(payload["password"]), is_admin=False
        )
    except UsernameTakenError:
        return jsonify({"error": "Username already exists"}), 400
    return jsonify({"message": "User created successfully", "user_id": uid}), 201


@app_bp.route("/users/<int:user_id>", methods=["GET"])
@require_jwt
def get_user(user_id: int):
    user = store.user_get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user), 200


@app_bp.route("/users", methods=["GET"])
@require_jwt
def list_users():
    if not request_is_admin():
        return jsonify({"error": "Forbidden"}), 403
    users = store.users_list_all()
    return jsonify(users), 200


@app_bp.route("/users/<int:user_id>/admin", methods=["PATCH"])
@require_jwt
def set_user_admin(user_id: int):
    if not request_is_admin():
        return jsonify({"error": "Forbidden"}), 403
    payload = request.get_json(silent=True) or {}
    is_admin = payload.get("is_admin")
    if not isinstance(is_admin, bool):
        return jsonify({"error": "is_admin (bool) is required"}), 400
    if not store.user_get(user_id):
        return jsonify({"error": "User not found"}), 404
    store.user_set_admin(user_id, is_admin)
    return jsonify(store.user_get(user_id)), 200
