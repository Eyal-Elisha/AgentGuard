"""Shared utility functions used across Stage A rule implementations."""

from __future__ import annotations

import ipaddress
import re
import warnings
from functools import lru_cache
from typing import List, Tuple

from publicsuffix2 import get_public_suffix, get_sld

from backend.feature_extraction.feature_extractor import ExtractedFeatures
from backend.analysis.stages.stage_a.data import (
    BRAND_DOMAINS,
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


@lru_cache(maxsize=1)
def official_sld_labels() -> frozenset[str]:
    """The registrable label of every official brand domain.

    Legitimate brands are one or two edits apart often enough (spotify and
    shopify, discover and discord) that the typosquatting rule has to know
    which labels are real before it starts measuring distance.
    """
    return frozenset(
        get_sld_label(official)
        for domains in BRAND_DOMAINS.values()
        for official in domains
    )


@lru_cache(maxsize=1)
def brand_token_patterns() -> Tuple[Tuple[str, Tuple[str, ...], "re.Pattern[str]"], ...]:
    """Per-brand `(brand, official domains, matcher)`, for brands of 3+ letters.

    The matcher requires the brand to be flanked by non-letters, so
    'paypal-login', 'secure.amazon' and 'amazon1' match while 'pineapple' does
    not accidentally match apple, nor 'discovery' discover.
    """
    return tuple(
        (brand, tuple(official), re.compile(r"(?<![a-z])" + re.escape(brand) + r"(?![a-z])"))
        for brand, official in BRAND_DOMAINS.items()
        if len(brand) >= 3
    )


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
    """Single-edit typosquat of a brand label, tuned for precision.

    Plain Levenshtein on short or common labels collides with ordinary words and
    unrelated brands (ring/bing, allure/azure, moen/msn, bbc/bac), and because
    this rule feeds a block decision those collisions are expensive. We therefore
    require *all* of:

    - both labels at least 5 chars — short brands (bac, max, msn, bing, ebay …)
      are the main false-positive generators, so they are not valid edit-distance
      targets here;
    - lengths within 1 of each other;
    - exactly one edit (insert / delete / substitute);
    - the same first character — real typos keep the recognizable brand start,
      which rejects first-letter swaps like ``maple`` vs ``apple``.

    Homoglyph / confusable impersonation (``paypa1`` → ``paypal``) is a separate,
    higher-precision signal handled by the caller and is *not* gated by these
    length rules.
    """
    if len(candidate) < 5 or len(target) < 5:
        return False
    if abs(len(candidate) - len(target)) > 1:
        return False
    if candidate[0] != target[0]:
        return False
    return levenshtein(candidate, target) == 1
