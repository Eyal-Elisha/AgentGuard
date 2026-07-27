"""Deterministic rule implementations for Stage A (Rules 1–9)."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Dict, Tuple
from urllib.parse import urlparse

from backend.custom_blacklist import custom_blacklist_entry_matches, custom_blacklist_matches
from backend.feature_extraction.feature_extractor import ExtractedFeatures
from backend.analysis.stages.stage_a.blacklist import blacklist_cache
from backend.analysis.stages.stage_a.data import (
    BRAND_DOMAINS,
    HIGH_ABUSE_TLDS,
    SENSITIVE_INPUT_TYPES,
    SENSITIVE_NAME_RE,
)
from backend.analysis.stages.stage_a.helpers import (
    domain_matches,
    get_sld_label,
    has_sensitive_inputs,
    is_ip,
    is_loopback_host,
    is_typosquat,
    normalize_confusables,
    strip_www,
)


@lru_cache(maxsize=1)
def _official_sld_labels() -> frozenset[str]:
    """Every registrable SLD label listed as an official brand domain.

    Used so legitimate domains (e.g. spotify vs shopify) are not flagged as mutual
    typosquats — Levenshtein cannot tell them from real attacks.
    """
    labels: set[str] = set()
    for domains in BRAND_DOMAINS.values():
        for official in domains:
            labels.add(get_sld_label(official))
    return frozenset(labels)


def rule_domain_blacklist(features: ExtractedFeatures) -> Tuple[float, str]:
    """Rule 1 — Domain in Popular Blacklist. Hard block."""
    host = strip_www(features.host)
    parts = host.split(".")
    for i in range(len(parts) - 1):
        candidate = ".".join(parts[i:])
        listed, source = blacklist_cache.is_listed(candidate)
        if listed:
            return 1.0, f"Domain '{candidate}' found in {source} threat database"
    return 0.0, "Domain not found in threat database"


def rule_unencrypted_connection(features: ExtractedFeatures) -> Tuple[float, str]:
    """Rule 2 — Unencrypted or Invalid Secure Connection. Hard block."""
    if features.scheme != "https":
        if is_loopback_host(features.host):
            return 0.0, "Local loopback; HTTP is acceptable for local development"
        return 1.0, f"Connection is unencrypted ('{features.scheme}://')"
    return 0.0, "Connection is encrypted (HTTPS)"


def rule_sensitive_fields(features: ExtractedFeatures) -> Tuple[float, str]:
    """Rule 3 — Sensitive Fields Present."""
    if has_sensitive_inputs(features):
        return 1.0, "Page contains input fields associated with credential or secret collection"
    return 0.0, "No sensitive input fields detected"


@lru_cache(maxsize=1)
def _brand_token_patterns() -> Tuple[Tuple[str, Tuple[str, ...], "re.Pattern[str]"], ...]:
    """Compile a word-boundary matcher per brand (length >= 3).

    The brand must be flanked by non-letters (separators, digits, or string
    edges) so 'paypal-login', 'secure.amazon', and 'amazon1' match while
    dictionary collisions like 'pineapple' (→apple) or 'discovery' (→discover)
    do not.
    """
    patterns = []
    for brand, official in BRAND_DOMAINS.items():
        if len(brand) < 3:
            continue
        patterns.append((
            brand,
            tuple(official),
            re.compile(r"(?<![a-z])" + re.escape(brand) + r"(?![a-z])"),
        ))
    return tuple(patterns)


def rule_brand_domain_mismatch(features: ExtractedFeatures) -> Tuple[float, str]:
    """Rule 4 — Brand Domain Mismatch.

    Flags three impersonation patterns on a non-official domain:
      1. Brand named in the page <title>.
      2. Brand embedded as a token in the hostname (e.g. 'amazon.zaolir.cfd').
      3. Brand token in the URL path on a page that also collects credentials
         (path-only matches are gated on sensitive inputs to avoid flagging
         benign pages that merely mention a brand).
    """
    if not features.dom:
        return 0.0, "No DOM content to inspect"
    title = features.dom.page_title.lower()
    host = strip_www(features.host)
    path = urlparse(features.url).path.lower()
    has_sensitive = has_sensitive_inputs(features)

    for brand, official_domains in BRAND_DOMAINS.items():
        if brand in title and not domain_matches(host, official_domains):
            return 1.0, (
                f"Page title references brand '{brand}' "
                f"but is hosted on non-official domain '{host}'"
            )

    for brand, official_domains, pattern in _brand_token_patterns():
        if domain_matches(host, official_domains):
            continue
        if pattern.search(host):
            return 1.0, (
                f"Hostname '{host}' embeds brand '{brand}' "
                f"but is not an official '{brand}' domain"
            )
        if has_sensitive and pattern.search(path):
            return 1.0, (
                f"URL path references brand '{brand}' on a credential-collecting "
                f"page hosted off '{brand}'s official domain ('{host}')"
            )

    return 0.0, "No brand-domain mismatch detected"



# Patterns that extract a redirect target URL from various redirect vectors
_REDIRECT_PATTERNS = [
    # <meta http-equiv="refresh" content="0; url=...">
    (re.compile(r'http-equiv=["\']refresh["\'][^>]*content=["\'][^"\']*url\s*=\s*([^"\'>\s;]+)', re.IGNORECASE), "meta-refresh"),
    (re.compile(r'content=["\'][^"\']*url\s*=\s*([^"\'>\s;]+)[^"\']*["\'][^>]*http-equiv=["\']refresh["\']', re.IGNORECASE), "meta-refresh"),
    # JS: window.location = "..." / window.location.href = "..." / location.replace("...") / location.assign("...")
    (re.compile(r'(?:window\.)?location(?:\.href)?\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE), "JS location assignment"),
    (re.compile(r'location\.(?:replace|assign)\s*\(\s*["\']([^"\']+)["\']', re.IGNORECASE), "JS location redirect"),
    # <body onload="window.location=..."> or similar event attributes
    (re.compile(r'on(?:load|DOMContentLoaded)\s*=\s*["\'][^"\']*(?:window\.)?location\s*=\s*["\']?([^"\'>\s]+)', re.IGNORECASE), "onload redirect"),
    # <img onerror="window.location=...">
    (re.compile(r'onerror\s*=\s*["\'][^"\']*(?:window\.)?location\s*=\s*["\']?([^"\'>\s]+)', re.IGNORECASE), "onerror redirect"),
]


def rule_unexpected_redirect(features: ExtractedFeatures) -> Tuple[float, str]:
    """Rule 5 — Unexpected Redirect During Sensitive Interaction.

    Checks meta-refresh, inline JS location assignments, and HTML event
    handler redirects (onload, onerror) for external domain targets.
    """
    if not features.dom or not has_sensitive_inputs(features):
        return 0.0, "No sensitive interaction context to evaluate"

    body = features.raw_body
    if not body:
        return 0.0, "No page body to inspect"

    page_host = strip_www(features.host)

    for pattern, vector in _REDIRECT_PATTERNS:
        for match in pattern.finditer(body):
            target = match.group(1).strip()
            redirect_host = urlparse(target).hostname or ""
            if redirect_host and strip_www(redirect_host) != page_host:
                return 1.0, (
                    f"{vector} redirects to external domain '{redirect_host}' "
                    f"during a sensitive interaction"
                )

    return 0.0, "No unexpected external redirect detected during sensitive interaction"


def rule_external_form_action(features: ExtractedFeatures) -> Tuple[float, str]:
    """Rule 6 — External Form Action."""
    if not features.dom:
        return 0.0, "No DOM content to inspect"
    page_host = strip_www(features.host)
    for form in features.dom.forms:
        if not form.action_host:
            continue
        if strip_www(form.action_host) != page_host:
            has_sensitive = any(
                inp.get("type") in SENSITIVE_INPUT_TYPES
                or SENSITIVE_NAME_RE.search(inp.get("name", "") + " " + inp.get("id", ""))
                for inp in form.inputs
            )
            if has_sensitive:
                return 1.0, (
                    f"A form with sensitive fields submits to "
                    f"external domain '{form.action_host}'"
                )
    return 0.0, "No external form action with sensitive fields detected"


def rule_typosquatting(features: ExtractedFeatures) -> Tuple[float, str]:
    """Rule 7 — Typosquatting Domain Detection. Hard block.

    Detects two attack patterns:
      1. Confusable/homoglyph — normalized label matches official but original doesn't
         (e.g. paypa1.com, pаypal.com with Cyrillic а)
      2. Edit-distance typosquat — see ``is_typosquat`` (not raw ≤2 edits on short strings)
         (e.g. payal.com, papyal.com)
    """
    host = strip_www(features.host)
    if is_ip(host):
        return 0.0, "IP address — typosquatting check not applicable"

    original_label = get_sld_label(host)
    normalized_label = get_sld_label(normalize_confusables(host))

    # Legitimate brand site (spotify.com, shopify.com, …): do not compare to other brands.
    # Only when the label is unchanged by confusable normalization — otherwise paypa1→paypal
    # must still be caught by the confusable / edit-distance logic below.
    if (
        original_label == normalized_label
        and normalized_label in _official_sld_labels()
    ):
        return 0.0, "Domain label is a known official brand (not a typosquat of another brand)"

    for _, official_domains in BRAND_DOMAINS.items():
        for official in official_domains:
            official_label = get_sld_label(official)
            # Confusable attack: normalization collapses the fake label onto the real one
            if normalized_label == official_label and original_label != official_label:
                return 1.0, (
                    f"Domain '{host}' uses confusable characters to impersonate '{official}'"
                )
            # Edit-distance typosquat
            if normalized_label != official_label and is_typosquat(normalized_label, official_label):
                return 1.0, f"Domain '{host}' appears to be a typosquat of '{official}'"

    return 0.0, "No typosquatting pattern detected"


def rule_ip_based_url(features: ExtractedFeatures) -> Tuple[float, str]:
    """Rule 8 — IP Based URL Usage."""
    if is_ip(features.host):
        return 1.0, f"Page accessed via raw IP address '{features.host}'"
    return 0.0, "Page uses a registered domain name"


def rule_suspicious_tld(features: ExtractedFeatures) -> Tuple[float, str]:
    """Rule 10 — High-Abuse Top-Level Domain.

    Weak, non-blocking signal: many phishing pages sit on free/cheap TLDs.
    Legitimate sites use them too, so this only nudges the score and is meant
    to stack with brand/host signals rather than fire alone.
    """
    host = strip_www(features.host)
    if not host or is_ip(host):
        return 0.0, "No registrable domain to inspect"
    tld = host.rsplit(".", 1)[-1]
    if tld in HIGH_ABUSE_TLDS:
        return 1.0, f"Domain uses '.{tld}', a top-level domain frequently abused for phishing"
    return 0.0, "Top-level domain is not in the high-abuse list"


def _host_matches_blacklist_entry(host_stripped: str, entry_host: str) -> bool:
    return bool(entry_host) and (
        host_stripped == entry_host or host_stripped.endswith("." + entry_host)
    )


def rule_custom_blacklist(
    features: ExtractedFeatures,
    custom_blacklist: frozenset,
) -> Tuple[float, str]:
    """Rule 9 — Custom Local Blacklist. Hard block."""
    if not custom_blacklist:
        return 0.0, "Custom blacklist not configured"
    if custom_blacklist_matches(features.host, features.url, custom_blacklist):
        return 1.0, f"URL '{features.url}' matches the custom local blacklist"
    return 0.0, "Not found in custom local blacklist"


# Dispatch map — rule_id → function (rule_custom_blacklist handled separately)
RULE_FN: Dict[str, callable] = {
    "domain_blacklist":       rule_domain_blacklist,
    "unencrypted_connection": rule_unencrypted_connection,
    "sensitive_fields":       rule_sensitive_fields,
    "brand_domain_mismatch":  rule_brand_domain_mismatch,
    "unexpected_redirect":    rule_unexpected_redirect,
    "external_form_action":   rule_external_form_action,
    "typosquatting":          rule_typosquatting,
    "ip_based_url":           rule_ip_based_url,
    "suspicious_tld":         rule_suspicious_tld,
}
