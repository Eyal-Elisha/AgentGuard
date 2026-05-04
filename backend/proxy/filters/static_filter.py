"""Flags URLs that look like static assets instead of navigable pages."""

from __future__ import annotations

from urllib.parse import urlparse


def is_likely_static_subresource(url: str) -> bool:
    try:
        path = urlparse(url).path or ""
    except Exception:
        path = ""
    path = path.lower()

    static_exact = {"/favicon.ico", "/robots.txt"}
    if path in static_exact:
        return True

    static_suffixes = (
        ".ico",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".bmp",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".otf",
        ".js",
        ".css",
        ".mjs",
        ".map",
        ".mp4",
        ".webm",
        ".mp3",
        ".wav",
    )

    return path.endswith(static_suffixes)
