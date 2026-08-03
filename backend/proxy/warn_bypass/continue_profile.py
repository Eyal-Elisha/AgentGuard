"""What "Continue anyway" leaves behind once the token has been redeemed.

Redeeming a token registers two short-lived allowances for the host:

* the exact URL, once, so the document the 302 pointed at renders instead
  of bouncing straight back into the interstitial.
* a subresource window: a couple of minutes in which non-document GETs on
  the same host also skip it, so the page can finish loading.

Both live in process memory and are lost when mitmweb restarts.
"""

from __future__ import annotations

import threading
import time
from typing import Dict, Tuple

from .urls import normalize_url

#: How long a page has to load its subresources before warnings resume.
DEFAULT_SUBRESOURCE_SUPPRESS_SECONDS: float = 120.0

#: How long the pending exact-URL allow survives if the browser never follows
#: the redirect.
EXACT_ALLOW_TTL_SECONDS: float = 5 * 60.0

_exact_lock = threading.Lock()
# (host, normalized url) -> monotonic expiry
_exact_allows: Dict[Tuple[str, str], float] = {}

_subresource_lock = threading.Lock()
# host -> monotonic expiry
_subresource_suppress: Dict[str, float] = {}


def register_continue_anyway(host: str, clean_url: str) -> None:
    """Record both allowances for `host` after a token was redeemed."""
    host = (host or "").lower()
    if not host:
        return
    now = time.monotonic()
    with _exact_lock:
        _sweep_exact(now)
        _exact_allows[(host, normalize_url(clean_url))] = now + EXACT_ALLOW_TTL_SECONDS
    open_subresource_window(host)


def should_suppress_warn_interstitial(flow) -> bool:
    """Whether a WARN on this flow should skip the interstitial.

    The exact-URL match is tried first and deliberately does not depend on
    Fetch Metadata: real browsers send `sec-fetch-dest: empty` often enough
    that trusting those headers alone would re-show the interstitial and put
    the user back in the loop the redirect just broke.
    """
    if flow.request.method.upper() != "GET":
        return False
    host = (flow.request.host or "").lower()
    if _consume_exact_allow(host, flow.request.pretty_url):
        return True
    if _is_probably_main_document_navigation(flow):
        return False
    return subresource_window_active(host)


def open_subresource_window(host: str) -> None:
    """Start (or extend) the subresource grace period for `host`."""
    host = (host or "").lower()
    if not host:
        return
    now = time.monotonic()
    with _subresource_lock:
        _sweep_subresource(now)
        _subresource_suppress[host] = now + DEFAULT_SUBRESOURCE_SUPPRESS_SECONDS


def subresource_window_active(host: str) -> bool:
    host = (host or "").lower()
    if not host:
        return False
    now = time.monotonic()
    with _subresource_lock:
        _sweep_subresource(now)
        expiry = _subresource_suppress.get(host)
        return expiry is not None and expiry >= now


def clear_continue_anyway_for_host(host: str) -> None:
    """Forget every allowance for one host."""
    host = (host or "").lower()
    with _subresource_lock:
        _subresource_suppress.pop(host, None)
    with _exact_lock:
        for key in [k for k in _exact_allows if k[0] == host]:
            _exact_allows.pop(key, None)


def _consume_exact_allow(host: str, request_url: str) -> bool:
    """True once, if this request is the pending exact continue URL."""
    host = (host or "").lower()
    if not host:
        return False
    now = time.monotonic()
    key = (host, normalize_url(request_url))
    with _exact_lock:
        _sweep_exact(now)
        expiry = _exact_allows.get(key)
        if expiry is None or expiry < now:
            return False
        _exact_allows.pop(key, None)
        return True


def _is_probably_main_document_navigation(flow) -> bool:
    """Fetch Metadata when the browser sends it, permissive when it does not."""
    if flow.request.method.upper() != "GET":
        return False
    dest = (flow.request.headers.get("sec-fetch-dest") or "").lower()
    mode = (flow.request.headers.get("sec-fetch-mode") or "").lower()
    if dest == "document" or mode == "navigate":
        return True
    return dest == "" and mode == ""


def _sweep_exact(now: float) -> None:
    for key in [k for k, expiry in _exact_allows.items() if expiry < now]:
        _exact_allows.pop(key, None)


def _sweep_subresource(now: float) -> None:
    for host in [h for h, expiry in _subresource_suppress.items() if expiry < now]:
        _subresource_suppress.pop(host, None)
