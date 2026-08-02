"""Bypass state for the Warn interstitial.

Cookie-based bypass is fragile in HTTPS-via-MITM setups, so we use:

1. **One-shot tokens** (`mint_bypass_token` / `consume_bypass_token`)
   The interstitial's "Continue anyway" link points at
   `originalUrl?_agentguard_bypass=<token>`. The proxy validates and consumes
   the token, responds with 302 to the clean URL, then registers a **continue
   profile** for that host (see below).

2. **Continue profile** (`register_continue_anyway`)
   * **Exact URL allow** — the first main-document GET to the same normalized
     URL as the 302 target can return WARN from the backend without showing the
     interstitial, so the real page renders instead of a redirect loop.
   * **Subresource window** — for a short time, non-document GETs (scripts,
     images, XHR, etc. via Fetch Metadata) also skip the interstitial while
     still going through normal backend evaluation and logging.

Unlike the old host "clean pass", the backend is **always** consulted: events
are logged and contextual rules still see session history. Only the **warn
UI** is suppressed for those narrow cases.

Both stores live in process memory; restarting mitmweb clears state.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


BYPASS_QUERY_PARAM: str = "_agentguard_bypass"

DEFAULT_TOKEN_TTL_SECONDS: float = 5 * 60.0
# After "Continue anyway", subresource requests on this host skip the warn
# interstitial briefly so the page can load; top-level navigations to new URLs
# are not covered (except the one-shot exact URL match).
DEFAULT_SUBRESOURCE_SUPPRESS_SECONDS: float = 120.0
# Pending exact-match entries expire if the browser never follows the redirect.
EXACT_ALLOW_TTL_SECONDS: float = 5 * 60.0


def _normalize_netloc(netloc: str, scheme: str) -> str:
    if not netloc:
        return netloc
    lower = netloc.lower()
    if scheme == "https" and lower.endswith(":443"):
        return lower[:-4]
    if scheme == "http" and lower.endswith(":80"):
        return lower[:-3]
    return lower


def _normalize_url(url: str) -> str:
    """Canonical form for comparing continue URL vs incoming request URL."""
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "https").lower()
    netloc = _normalize_netloc((parts.netloc or "").lower(), scheme)
    path = parts.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    pairs = sorted(parse_qsl(parts.query, keep_blank_values=True))
    query = urlencode(pairs)
    return urlunsplit((scheme, netloc, path, query, ""))


# ---------------------------------------------------------------------------
# One-shot redirect tokens
# ---------------------------------------------------------------------------

@dataclass
class _PendingBypass:
    host: str
    expires_at: float


class WarnBypassStore:
    """Thread-safe one-shot token store. Tokens are valid until consumed or
    until their TTL expires."""

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
        """Remove the token and return the host it was minted for, or None
        if the token is missing/expired."""
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
        return entry.host

    def _sweep(self, current: float) -> None:
        expired = [tok for tok, entry in self._tokens.items() if entry.expires_at < current]
        for tok in expired:
            self._tokens.pop(tok, None)


# ---------------------------------------------------------------------------
# Continue anyway: exact URL + subresource interstitial suppression
# ---------------------------------------------------------------------------

_store = WarnBypassStore()
_exact_lock = threading.Lock()
# (host, normalized_url) -> monotonic expiry
_exact_allows: Dict[Tuple[str, str], float] = {}
_subresource_lock = threading.Lock()
# host -> monotonic expiry for subresource / non-navigate GET suppression
_subresource_suppress: Dict[str, float] = {}


def _sweep_exact(current: float) -> None:
    dead = [k for k, exp in _exact_allows.items() if exp < current]
    for k in dead:
        _exact_allows.pop(k, None)


def _sweep_subresource(current: float) -> None:
    dead = [h for h, exp in _subresource_suppress.items() if exp < current]
    for h in dead:
        _subresource_suppress.pop(h, None)


def register_continue_anyway(host: str, clean_url: str) -> None:
    """After a bypass token is redeemed, allow one document load + a short
    subresource window without showing the warn interstitial (backend still runs)."""
    host = (host or "").lower()
    if not host:
        return
    current = time.monotonic()
    key = (host, _normalize_url(clean_url))
    with _exact_lock:
        _sweep_exact(current)
        _exact_allows[key] = current + EXACT_ALLOW_TTL_SECONDS
    with _subresource_lock:
        _sweep_subresource(current)
        _subresource_suppress[host] = current + DEFAULT_SUBRESOURCE_SUPPRESS_SECONDS


def try_consume_exact_continue_allow(host: str, request_url: str) -> bool:
    """Return True once if this request matches a pending exact continue URL."""
    host = (host or "").lower()
    if not host:
        return False
    current = time.monotonic()
    key = (host, _normalize_url(request_url))
    with _exact_lock:
        _sweep_exact(current)
        exp = _exact_allows.get(key)
        if exp is None or exp < current:
            return False
        _exact_allows.pop(key, None)
        return True


def _subresource_suppress_active(host: str) -> bool:
    host = (host or "").lower()
    if not host:
        return False
    current = time.monotonic()
    with _subresource_lock:
        _sweep_subresource(current)
        exp = _subresource_suppress.get(host)
        return exp is not None and exp >= current


def _is_probably_main_document_navigation(flow) -> bool:
    """Use Fetch Metadata when present; fall back to permissive heuristics."""
    if flow.request.method.upper() != "GET":
        return False
    dest = (flow.request.headers.get("sec-fetch-dest") or "").lower()
    mode = (flow.request.headers.get("sec-fetch-mode") or "").lower()
    if dest == "document":
        return True
    if mode == "navigate":
        return True
    if dest == "" and mode == "":
        return True
    return False


def should_suppress_warn_interstitial(flow) -> bool:
    """If the backend said WARN, suppress the interstitial for this hop only
    when continue-anyway rules cover it (and consume exact allow if applicable)."""
    if flow.request.method.upper() != "GET":
        return False
    host = (flow.request.host or "").lower()
    # Match the post-redirect URL first. Relying on Sec-Fetch-* alone breaks
    # real browsers (e.g. dest=empty) and would re-show the interstitial loop.
    if try_consume_exact_continue_allow(host, flow.request.pretty_url):
        return True
    if _is_probably_main_document_navigation(flow):
        return False
    return _subresource_suppress_active(host)


def clear_continue_anyway_for_host(host: str) -> None:
    """Test helper: remove all continue state for one host."""
    host = (host or "").lower()
    with _subresource_lock:
        _subresource_suppress.pop(host, None)
    with _exact_lock:
        keys = [k for k in _exact_allows if k[0] == host]
        for k in keys:
            _exact_allows.pop(k, None)


# Backwards-compatible names for tests / older call sites
def register_clean_pass(host: str) -> None:
    """Deprecated: was a 5-minute full backend bypass. Use register_continue_anyway."""
    host = (host or "").lower()
    with _subresource_lock:
        _subresource_suppress[host] = time.monotonic() + DEFAULT_SUBRESOURCE_SUPPRESS_SECONDS


def has_clean_pass(host: str) -> bool:
    """Deprecated: approximate old API — True only while subresource window active."""
    return _subresource_suppress_active((host or "").lower())


def revoke_clean_pass(host: str) -> None:
    clear_continue_anyway_for_host(host)


def mint_bypass_token(host: str) -> str:
    return _store.mint(host)


def consume_bypass_token(token: str) -> Optional[str]:
    return _store.consume(token)
