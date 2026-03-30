from __future__ import annotations

from mitmproxy import http
from urllib.parse import urlparse

from backend.proxy.filters.action_filter import is_action_request


def _path_looks_like_page(url: str) -> bool:
    try:
        path = urlparse(url).path or ""
    except Exception:
        path = ""
    path = path.lower()
    if path.endswith("/"):
        return True
    if path.endswith(".html"):
        return True
    last = path.rsplit("/", 1)[-1]
    if last and "." not in last:
        return True
    return False


def determine_forward_reason(flow: http.HTTPFlow) -> tuple[bool, str]:
    headers = flow.request.headers
    method = flow.request.method.upper()

    xrw = headers.get("x-requested-with", "").lower()
    if xrw == "xmlhttprequest":
        return False, "xhr"

    sec_fetch_dest = headers.get("sec-fetch-dest", "").lower()
    sec_fetch_mode = headers.get("sec-fetch-mode", "").lower()
    sec_fetch_user = headers.get("sec-fetch-user", "")
    accept = headers.get("accept", "").lower()
    content_type = headers.get("content-type", "").lower()
    upgrade_insecure = headers.get("upgrade-insecure-requests", "").lower()

    if sec_fetch_dest == "document" or sec_fetch_mode == "navigate" or upgrade_insecure == "1":
        return True, "top-level-navigation"

    if "text/html" in accept or "application/xhtml+xml" in accept:
        return True, "accept-html"

    if sec_fetch_user == "?1":
        return True, "user-activation"

    if is_action_request(flow):
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                return True, "form-submission"
            return False, "json-post-skip"
        return True, "get-with-body"

    if method == "GET":
        url = flow.request.pretty_url
        if _path_looks_like_page(url):
            return True, "likely-navigation"
        return False, "get-skip"

    return False, "other-skip"
