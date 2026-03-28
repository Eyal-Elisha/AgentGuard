"""Password hashing and JWT helpers (minimal for now).
Later: tighten JWT issue/decode (claims, TTL, optional revocation) and add production auth hygiene (rate limits, secret handling, HTTPS)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from flask import Request, current_app, g, jsonify, request

_ph = PasswordHasher()


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(hash_str: str, plain: str) -> bool:
    try:
        return _ph.verify(hash_str, plain)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def issue_token(user_id: int, username: str, is_admin: bool) -> str:
    secret = current_app.config["JWT_SECRET"]
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "is_admin": is_admin,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=24)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any] | None:
    secret = current_app.config["JWT_SECRET"]
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def get_bearer_token(req: Request) -> str | None:
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return auth[7:].strip() or None


def get_optional_auth_payload(req: Request) -> tuple[dict[str, Any] | None, str | None]:
    token = get_bearer_token(req)
    if not token:
        return None, None
    payload = decode_token(token)
    if payload is None:
        return None, "Unauthorized"
    return payload, None


def require_jwt(f: Callable) -> Callable:
    """Require a valid JWT unless REQUIRE_AUTH is false."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_app.config.get("REQUIRE_AUTH", True):
            return f(*args, **kwargs)
        payload, err = get_optional_auth_payload(request)
        if err or payload is None:
            return jsonify({"error": "Unauthorized"}), 401
        g.jwt_user_id = payload["sub"]
        g.jwt_username = payload.get("username")
        g.jwt_is_admin = payload.get("is_admin", False)
        return f(*args, **kwargs)

    return wrapper
