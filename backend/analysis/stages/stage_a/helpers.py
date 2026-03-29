"""Shared utility functions used across Stage A rule implementations."""

from __future__ import annotations

import ipaddress
import re
import warnings
from typing import List

from publicsuffix2 import get_public_suffix, get_sld

from backend.feature_extraction.feature_extractor import ExtractedFeatures
from backend.analysis.stages.stage_a.data import (
    CHAR_CONFUSABLES,
    MULTI_CHAR_SUBS,
    SENSITIVE_INPUT_TYPES,
    SENSITIVE_NAME_RE,
)


def strip_www(host: str) -> str:
    return re.sub(r"^www\.", "", host.lower())


def is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def is_loopback_host(host: str) -> bool:
    """True if host is localhost or a loopback IP (so local HTTP is not flagged)."""
    if not host:
        return False
    host = strip_www(host)
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def domain_matches(host: str, official_domains: List[str]) -> bool:
    """True if host equals or is a subdomain of any official domain."""
    host = strip_www(host)
    for d in official_domains:
        if host == d or host.endswith("." + d):
            return True
    return False


def has_sensitive_inputs(features: ExtractedFeatures) -> bool:
    if not features.dom:
        return False
    for form in features.dom.forms:
        for inp in form.inputs:
            if inp.get("type") in SENSITIVE_INPUT_TYPES:
                return True
            combined = inp.get("name", "") + " " + inp.get("id", "")
            if SENSITIVE_NAME_RE.search(combined):
                return True
    return False


def get_sld_label(host: str) -> str:
    """Return the second-level domain label using the Public Suffix List.

    e.g. 'login.paypal.com'   → 'paypal'
         'evil.paypal.co.uk'  → 'evil'   (correct — not impersonating paypal)
    """
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="publicsuffix2")
        registrable = get_sld(host)
        public_suffix = get_public_suffix(host)
    if not registrable:
        return host
    if public_suffix:
        suffix_dot = "." + public_suffix
        if registrable.endswith(suffix_dot):
            return registrable[: -len(suffix_dot)]
    return registrable.split(".")[0]


def normalize_confusables(domain: str) -> str:
    """Normalize Unicode confusables and common visual substitutions."""
    domain = domain.lower()
    for multi, canonical in MULTI_CHAR_SUBS:
        domain = domain.replace(multi, canonical)
    return "".join(CHAR_CONFUSABLES.get(ch, ch) for ch in domain)


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        return levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for ca in a:
        curr = [prev[0] + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]


def is_typosquat(candidate: str, target: str) -> bool:
    """Heuristic: Levenshtein alone is too loose on short labels (e.g. forter vs force).

    - Distance 1: treat as typosquat (single typo / insertion / deletion).
    - Distance 2: only if first and last characters match the target — catches swaps and
      middle edits (papyal vs paypal) while rejecting many unrelated 2-edit collisions.
    """
    if len(candidate) < 3 or len(target) < 3:
        return False
    if abs(len(candidate) - len(target)) > 2:
        return False
    d = levenshtein(candidate, target)
    if d <= 0 or d > 2:
        return False
    if d == 1:
        return True
    # d == 2
    return candidate[0] == target[0] and candidate[-1] == target[-1]
