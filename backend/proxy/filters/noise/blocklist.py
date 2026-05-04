"""Host token and EasyPrivacy-backed blocklist matching helpers."""

from __future__ import annotations

import re

from backend.proxy.config.noise_config import NOISE_HOST_TOKENS

from .easyprivacy import _host_matches_easyprivacy


def _tokenize_host(host: str):
    if not host:
        return []
    return re.split(r"[.\-_]+", host.lower())


def _host_has_noise_token(host: str) -> bool:
    if not host:
        return False

    tokens = _tokenize_host(host)

    for t in tokens:
        if t in NOISE_HOST_TOKENS:
            return True

    if re.search(r"clients\d+", host):
        return True
    if re.search(r"gvt\d+", host):
        return True

    return False


def is_in_blocklist(host: str) -> bool:
    if not host:
        return False
    host = host.lower()

    if _host_has_noise_token(host):
        return True

    if _host_matches_easyprivacy(host):
        return True

    return False
