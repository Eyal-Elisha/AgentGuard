"""Validation for payloads sent from mitmproxy to the decision API."""

import re
from typing import Any
from urllib.parse import urlsplit

ALLOWED_PROXY_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})
MAX_PROXY_ENVELOPE_BYTES = 1_048_576
MAX_URL_BYTES = 8_192
MAX_BODY_BYTES = 512_000
MAX_HEADER_COUNT = 100
MAX_HEADER_NAME_BYTES = 256
MAX_HEADER_VALUE_BYTES = 8_192
MAX_TOTAL_HEADER_BYTES = 65_536
_HEADER_NAME = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_PAYLOAD_TYPES = frozenset({"REQUEST", "RESPONSE"})


def _byte_length(value: str) -> int:
    return len(value.encode("utf-8"))


def _validate_url(value: Any) -> tuple[str | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, "'url' must be a non-empty string"
    url = value.strip()
    if _byte_length(url) > MAX_URL_BYTES:
        return None, "'url' exceeds the size limit"
    if any(ord(char) < 32 or ord(char) == 127 for char in url):
        return None, "'url' contains control characters"
    try:
        parsed = urlsplit(url)
        _ = parsed.port
    except ValueError:
        return None, "'url' is malformed"
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None, "'url' must be an absolute HTTP or HTTPS URL"
    if parsed.username is not None or parsed.password is not None:
        return None, "'url' must not contain credentials"
    return url, None

def _validate_headers(value: Any) -> tuple[dict[str, str] | None, str | None]:
    if not isinstance(value, dict):
        return None, "'headers' must be an object"
    if len(value) > MAX_HEADER_COUNT:
        return None, "'headers' exceeds the count limit"
    normalized: dict[str, str] = {}
    total_bytes = 0
    for name, item in value.items():
        if not isinstance(name, str) or not _HEADER_NAME.fullmatch(name):
            return None, "'headers' contains an invalid name"
        if not isinstance(item, str) or "\r" in item or "\n" in item:
            return None, "'headers' contains an invalid value"
        name_bytes, value_bytes = _byte_length(name), _byte_length(item)
        if name_bytes > MAX_HEADER_NAME_BYTES or value_bytes > MAX_HEADER_VALUE_BYTES:
            return None, "'headers' contains an oversized entry"
        total_bytes += name_bytes + value_bytes
        if total_bytes > MAX_TOTAL_HEADER_BYTES:
            return None, "'headers' exceeds the total size limit"
        normalized[name] = item
    return normalized, None


def validate_proxy_payload(payload: Any) -> tuple[dict[str, Any] | None, str | None, int]:
    if not isinstance(payload, dict):
        return None, "JSON request body is required", 400
    missing = [key for key in ("url", "method", "headers", "body") if key not in payload]
    if missing:
        return None, f"Missing required fields: {', '.join(missing)}", 400
    url, error = _validate_url(payload["url"])
    if error:
        return None, error, 413 if "size limit" in error else 400
    method = payload["method"].strip().upper() if isinstance(payload["method"], str) else ""
    if method not in ALLOWED_PROXY_METHODS:
        return None, "'method' is not supported", 400
    headers, error = _validate_headers(payload["headers"])
    if error:
        return None, error, 413 if "limit" in error or "oversized" in error else 400
    body = "" if payload["body"] is None else payload["body"]
    if not isinstance(body, str):
        return None, "'body' must be a string or null", 400
    if _byte_length(body) > MAX_BODY_BYTES:
        return None, "'body' exceeds the size limit", 413
    payload_type = payload.get("type")
    if payload_type is not None and payload_type not in _PAYLOAD_TYPES:
        return None, "'type' must be REQUEST or RESPONSE", 400
    host = payload.get("host")
    if host is not None and (not isinstance(host, str) or host.lower() != urlsplit(url).hostname.lower()):
        return None, "'host' does not match the URL", 400
    return {**payload, "url": url, "method": method, "headers": headers, "body": body}, None, 200
