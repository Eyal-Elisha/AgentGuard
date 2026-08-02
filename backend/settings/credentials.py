"""The two secrets AgentGuard will not start without.

Both fail loudly when unset rather than falling back to a default, since a
default would mean either unsigned tokens or unencrypted logs.
"""

from __future__ import annotations

import os

from .env import read_env


def resolve_jwt_secret() -> str:
    """The HS256 signing secret. Always required — login issues JWTs even when
    REQUIRE_AUTH is off."""
    raw = os.environ.get("JWT_SECRET")
    secret = raw.strip() if isinstance(raw, str) else ""
    if secret:
        return secret
    raise RuntimeError("JWT_SECRET must be set")


def get_log_encryption_key() -> str:
    """The Fernet key for URLs, headers, scores and rule details at rest."""
    key = read_env("AGENTGUARD_LOG_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "AGENTGUARD_LOG_ENCRYPTION_KEY must be set before persisting logs. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    return key
