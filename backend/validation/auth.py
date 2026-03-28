"""Authentication-related payload validation."""

from __future__ import annotations

from .common import clean_string, require_dict


def validate_login_signup(payload: dict | None) -> tuple[dict | None, str | None]:
    payload, err = require_dict(payload)
    if err:
        return None, err

    username = clean_string(payload.get("username"), max_length=50)
    password = payload.get("password")

    if username is None:
        return None, "username is required"
    if not isinstance(password, str) or not password:
        return None, "password is required"

    return {"username": username, "password": password}, None
