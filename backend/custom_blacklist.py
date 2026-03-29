"""Shared custom blacklist parsing and matching helpers."""

from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import urlparse

_DEFAULT_BLACKLIST_FILENAME = "custom_blacklist.txt"


def _strip_www(host: str) -> str:
    return re.sub(r"^www\.", "", host.lower())


def parse_custom_blacklist_file_content(content: str) -> frozenset[str]:
    """One entry per line; # starts a comment; entries are lowercased."""
    entries: list[str] = []
    for line in content.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            entries.append(line.lower())
    return frozenset(entries)


def custom_blacklist_file_path() -> Path:
    return Path(__file__).resolve().parent / "proxy" / _DEFAULT_BLACKLIST_FILENAME


def load_custom_blacklist_file(path: Path) -> frozenset[str]:
    if not path.is_file():
        return frozenset()
    text = path.read_text(encoding="utf-8")
    return parse_custom_blacklist_file_content(text)


def _host_matches_blacklist_entry(host_stripped: str, entry_host: str) -> bool:
    return bool(entry_host) and (
        host_stripped == entry_host or host_stripped.endswith("." + entry_host)
    )


def _url_matches_blacklist_entry(entry: str, url_lc: str) -> bool:
    entry_base, has_entry_query, entry_query = entry.partition("?")
    url_base, has_url_query, url_query = url_lc.partition("?")

    if url_base.rstrip("/") != entry_base.rstrip("/"):
        return False
    if has_entry_query:
        return has_url_query and url_query == entry_query
    return True


def custom_blacklist_entry_matches(entry: str, *, host_stripped: str, url_lc: str) -> bool:
    """Host entries match subdomains; URL/path entries match the normalized target exactly."""
    entry = entry.strip().lower()
    if not entry:
        return False
    if "://" in entry:
        parsed = urlparse(entry)
        entry_host = _strip_www(parsed.hostname or "")
        if not (parsed.path or "").strip("/") and not parsed.query:
            return _host_matches_blacklist_entry(host_stripped, entry_host)
        return _url_matches_blacklist_entry(entry, url_lc)
    if "/" in entry or "?" in entry:
        return _url_matches_blacklist_entry(entry, url_lc)
    entry_host = _strip_www(entry.strip("."))
    return _host_matches_blacklist_entry(host_stripped, entry_host)


def custom_blacklist_matches(host: str, url: str, custom_blacklist: frozenset[str]) -> bool:
    """True if the host/URL pair matches any custom blacklist entry."""
    if not custom_blacklist:
        return False

    host_stripped = _strip_www(host)
    url_lc = url.lower()
    return any(
        custom_blacklist_entry_matches(entry, host_stripped=host_stripped, url_lc=url_lc)
        for entry in custom_blacklist
    )
