"""One-shot tokens minted for the interstitial's "Continue anyway" link.

A token is valid for exactly one redemption on the host it was minted for.
That is what stops the link from being reusable, shareable, or repayable after
the user has moved on. State is in process memory: restarting mitmweb
invalidates every outstanding token, which is the safe direction to fail.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

DEFAULT_TOKEN_TTL_SECONDS: float = 5 * 60.0


@dataclass
class _PendingBypass:
    host: str
    expires_at: float


class WarnBypassStore:
    """Thread-safe one-shot token store, valid until consumed or expired."""

    def __init__(self, ttl_seconds: float = DEFAULT_TOKEN_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._tokens: Dict[str, _PendingBypass] = {}
        self._lock = threading.Lock()

    def mint(self, host: str, *, now: Optional[float] = None) -> str:
        current = now if now is not None else time.monotonic()
        token = secrets.token_urlsafe(24)
        with self._lock:
            self._sweep(current)
            self._tokens[token] = _PendingBypass(host=host, expires_at=current + self._ttl)
        return token

    def consume(self, token: str, *, now: Optional[float] = None) -> Optional[str]:
        """Remove the token and return the host it was minted for.

        None when the token is unknown or expired — the caller cannot tell the
        two apart, and does not need to.
        """
        if not token:
            return None
        current = now if now is not None else time.monotonic()
        with self._lock:
            self._sweep(current)
            entry = self._tokens.pop(token, None)
        if entry is None or entry.expires_at < current:
            return None
        return entry.host

    def _sweep(self, current: float) -> None:
        expired = [token for token, entry in self._tokens.items() if entry.expires_at < current]
        for token in expired:
            self._tokens.pop(token, None)


_store = WarnBypassStore()


def mint_bypass_token(host: str) -> str:
    return _store.mint(host)


def consume_bypass_token(token: str) -> Optional[str]:
    return _store.consume(token)
