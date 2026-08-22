"""URL handling for the bypass flow."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

#: The query parameter carrying a one-shot bypass token.
BYPASS_QUERY_PARAM: str = "_agentguard_bypass"


def strip_query_param(url: str, param: str) -> str:
    """Return `url` with every occurrence of query parameter `param` removed."""
    parts = urlsplit(url)
    pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key != param
    ]
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(pairs, doseq=True), parts.fragment)
    )


def normalize_url(url: str) -> str:
    """Canonical form for comparing a registered continue URL to a request URL.

    The browser need not send back exactly what we redirected it to.
    the default port may be dropped, a trailing slash added, query parameters
    reordered, so both sides are reduced to the same shape before comparison.
    """
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "https").lower()
    netloc = _normalize_netloc((parts.netloc or "").lower(), scheme)
    path = parts.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    return urlunsplit((scheme, netloc, path, query, ""))


def _normalize_netloc(netloc: str, scheme: str) -> str:
    if not netloc:
        return netloc
    lower = netloc.lower()
    if scheme == "https" and lower.endswith(":443"):
        return lower[:-4]
    if scheme == "http" and lower.endswith(":80"):
        return lower[:-3]
    return lower
