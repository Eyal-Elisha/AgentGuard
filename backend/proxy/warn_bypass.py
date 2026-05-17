"""One-shot bypass tokens for the Warn interstitial.

Every time AgentGuard would Warn on a request, the proxy mints a fresh token
and embeds it in the interstitial's "Continue anyway" link. Clicking that link
re-fetches the same URL with `?_agentguard_bypass=<token>`. The proxy consumes
the token (single use), strips the query parameter, and lets that one request
through without re-prompting. A separate Warn on a different URL — or a repeat
visit to the same URL after the token is used — produces a fresh interstitial.

Tokens are kept in process memory because the mitmproxy addon is a single
long-lived Python process; an interrupted process simply discards pending
bypasses, which is the safe default.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional


BYPASS_QUERY_PARAM: str = "_agentguard_bypass"
DEFAULT_TOKEN_TTL_SECONDS: float = 5 * 60.0


@dataclass
class _PendingBypass:
    url: str
    expires_at: float


class WarnBypassStore:
    """Thread-safe one-shot token store with a TTL sweep on every access."""

    def __init__(self, ttl_seconds: float = DEFAULT_TOKEN_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._tokens: Dict[str, _PendingBypass] = {}
        self._lock = threading.Lock()

    def mint(self, url: str, *, now: Optional[float] = None) -> str:
        current = now if now is not None else time.monotonic()
        token = secrets.token_urlsafe(24)
        with self._lock:
            self._sweep(current)
            self._tokens[token] = _PendingBypass(url=url, expires_at=current + self._ttl)
        return token

    def consume(self, token: str, *, now: Optional[float] = None) -> Optional[str]:
        """Return the URL the token was minted for, or None if invalid/expired.

        The token is removed from the store on success (single-use).
        """
        if not token:
            return None
        current = now if now is not None else time.monotonic()
        with self._lock:
            self._sweep(current)
            entry = self._tokens.pop(token, None)
        if entry is None:
            return None
        if entry.expires_at < current:
            return None
        return entry.url

    def _sweep(self, current: float) -> None:
        # Caller holds the lock.
        expired = [tok for tok, entry in self._tokens.items() if entry.expires_at < current]
        for tok in expired:
            self._tokens.pop(tok, None)


_store = WarnBypassStore()


def mint_bypass_token(url: str) -> str:
    return _store.mint(url)


def consume_bypass_token(token: str) -> Optional[str]:
    return _store.consume(token)
