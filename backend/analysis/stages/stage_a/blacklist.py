"""Domain/URL blacklist checking via multiple threat intelligence sources.

Sources used:
  - PhishTank  (phishing-specific, free API — optionally authenticated via
                PHISHTANK_API_KEY env var for higher rate limits)
  - URLhaus    (abuse.ch malware URL feed, free, no key required)

Both checks run concurrently; a positive from either triggers the rule.
Results are cached in-memory with a TTL to avoid hammering the APIs.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Tuple, Dict
from urllib.parse import quote as url_encode

import requests


_PHISHTANK_ENDPOINT = "https://checkurl.phishtank.com/checkurl/"
_URLHAUS_ENDPOINT   = "https://urlhaus-api.abuse.ch/v1/host/"
_REQUEST_TIMEOUT    = 3   # seconds per request
_CACHE_TTL          = 3600  # 1 hour


class BlacklistCache:
    """
    Thread-safe TTL cache that queries PhishTank and URLhaus in parallel.

    Fails open — if both APIs are unreachable the check returns False so
    that a network outage never causes false blocks.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, Tuple[bool, str, float]] = {}  # domain → (listed, source, ts)
        self._lock = threading.Lock()

    def is_listed(self, domain: str) -> Tuple[bool, str]:
        """Return (is_malicious, source_note)."""
        with self._lock:
            entry = self._cache.get(domain)
            if entry is not None:
                listed, source, ts = entry
                if time.monotonic() - ts < _CACHE_TTL:
                    return listed, f"{source} (cached)"

        listed, source = self._query(domain)

        with self._lock:
            self._cache[domain] = (listed, source, time.monotonic())

        return listed, source

    def _query(self, domain: str) -> Tuple[bool, str]:
        """Run PhishTank and URLhaus checks; return on first positive."""
        results: Dict[str, Tuple[bool, str]] = {}
        lock = threading.Lock()

        def check_phishtank() -> None:
            try:
                payload: dict = {
                    "url": url_encode(f"http://{domain}"),
                    "format": "json",
                }
                api_key = os.getenv("PHISHTANK_API_KEY")
                if api_key:
                    payload["app_key"] = api_key

                resp = requests.post(
                    _PHISHTANK_ENDPOINT,
                    data=payload,
                    timeout=_REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
                # PhishTank: results.in_database == True and valid == True means it's a known phish
                pt_result = data.get("results", {})
                listed = pt_result.get("in_database", False) and pt_result.get("valid", False)
                with lock:
                    results["phishtank"] = (listed, "PhishTank")
            except Exception:
                with lock:
                    results["phishtank"] = (False, "PhishTank unavailable")

        def check_urlhaus() -> None:
            try:
                resp = requests.post(
                    _URLHAUS_ENDPOINT,
                    data={"host": domain},
                    timeout=_REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                listed = resp.json().get("query_status") == "is_host"
                with lock:
                    results["urlhaus"] = (listed, "URLhaus")
            except Exception:
                with lock:
                    results["urlhaus"] = (False, "URLhaus unavailable")

        threads = [
            threading.Thread(target=check_phishtank, daemon=True),
            threading.Thread(target=check_urlhaus, daemon=True),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for listed, source in results.values():
            if listed:
                return True, source

        return False, "not listed"


# Module-level singleton shared across all evaluations
blacklist_cache = BlacklistCache()
