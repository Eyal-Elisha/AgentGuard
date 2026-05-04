"""EasyPrivacy loading and domain matching for noise detection."""

from __future__ import annotations

import logging
import threading

from backend.proxy.config.noise_config import EASYPRIVACY_URL

EASYPRIVACY_DOMAINS: set[str] = set()
_logger = logging.getLogger(__name__)


def load_easyprivacy_domains():
    global EASYPRIVACY_DOMAINS

    try:
        _logger.debug("[AgentGuard] Loading EasyPrivacy list...")
        import requests as _requests

        session = _requests.Session()
        session.trust_env = False
        session.proxies = {}

        response = session.get(EASYPRIVACY_URL, timeout=10)

        domains = set()

        for line in response.text.splitlines():
            line = line.strip()

            if line.startswith("||") and "^" in line:
                domain = line.split("^")[0].replace("||", "")
                domains.add(domain)

        EASYPRIVACY_DOMAINS.clear()
        EASYPRIVACY_DOMAINS.update(domains)
        _logger.debug("[AgentGuard] Loaded %d noise domains", len(domains))

    except Exception:
        _logger.exception("[AgentGuard] Failed to load EasyPrivacy")
        EASYPRIVACY_DOMAINS.clear()


def _host_matches_easyprivacy(host: str) -> bool:
    host = host.lower()
    for domain in EASYPRIVACY_DOMAINS:
        d = domain.lower()
        if not d:
            continue

        if host == d or host.endswith("." + d):
            return True

        if d in host:
            return True
    return False


_thread = threading.Thread(target=load_easyprivacy_domains, daemon=True)
_thread.start()
