"""Request relevance filtering keeps proxy analysis focused."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from backend.custom_blacklist import custom_blacklist_matches
from backend.proxy.filter_requests import should_forward


def _flow(
    host: str = "example.com",
    path: str = "/",
    method: str = "GET",
    ua: str = "Mozilla/5.0 Chrome/120.0.0.0",
    headers: dict | None = None,
    *,
    port: int = 443,
) -> SimpleNamespace:
    request_headers = {
        "user-agent": ua,
        "accept": "text/html",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
    }
    if headers:
        request_headers.update(headers)
    req = SimpleNamespace(
        method=method,
        host=host,
        port=port,
        pretty_url=f"https://{host}{path}",
        headers=request_headers,
        content=b"",
    )
    return SimpleNamespace(request=req)


def test_noise_skips_when_not_on_custom_blacklist():
    with patch("backend.proxy.filter_requests.custom_blacklist_matches", return_value=False), patch(
        "backend.proxy.filter_requests.is_noise", return_value=True
    ):
        assert should_forward(_flow()) is False


def test_browser_get_request_is_forwarded_when_not_noise():
    with patch("backend.proxy.filter_requests.custom_blacklist_matches", return_value=False), patch(
        "backend.proxy.filter_requests.is_noise", return_value=False
    ):
        assert should_forward(_flow()) is True


def test_non_browser_request_is_not_forwarded():
    with patch("backend.proxy.filter_requests.is_noise", return_value=False):
        assert should_forward(_flow(ua="curl/8.0.1")) is False


def test_loopback_dashboard_and_api_skip_enforcement():
    """Using the proxy, local AgentGuard UI/API must not be MITM-evaluated."""
    with patch("backend.proxy.filter_requests.get_api_port", return_value=3000), patch(
        "backend.proxy.filter_requests.get_frontend_port", return_value=5000
    ), patch("backend.proxy.filter_requests.custom_blacklist_matches", return_value=False), patch(
        "backend.proxy.filter_requests.is_noise", return_value=False
    ):
        assert should_forward(_flow(host="127.0.0.1", port=5000)) is False
        assert should_forward(_flow(host="localhost", port=3000)) is False
        assert should_forward(_flow(host="127.0.0.1", port=9999)) is True


def test_shared_custom_blacklist_matcher_handles_subdomains():
    assert custom_blacklist_matches(
        "www.youtube.com",
        "https://www.youtube.com/watch?v=123",
        frozenset({"youtube.com"}),
    ) is True


def test_posthog_event_is_not_forwarded():
    flow = _flow(
        host="us.i.posthog.com",
        path="/i/v0/e/",
        method="POST",
        headers={"content-type": "application/json", "sec-fetch-dest": "empty"},
    )
    assert should_forward(flow) is False


def test_service_worker_is_not_forwarded():
    assert should_forward(_flow(path="/sw.js")) is False


def test_meaningful_form_post_is_forwarded():
    flow = _flow(
        path="/login",
        method="POST",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    with patch("backend.proxy.filter_requests.custom_blacklist_matches", return_value=False), patch(
        "backend.proxy.filter_requests.is_noise", return_value=False
    ):
        assert should_forward(flow) is True


def test_top_level_navigation_bypasses_noise_filter():
    with patch("backend.proxy.filter_requests.custom_blacklist_matches", return_value=False), patch(
        "backend.proxy.filter_requests.is_noise", return_value=True
    ):
        assert should_forward(_flow(host="cdn.example.com")) is True


def test_cross_site_json_get_is_not_forwarded():
    flow = _flow(
        host="ep2.adtrafficquality.google",
        path="/sodar/sodar2/254/runner.html",
        headers={
            "accept": "application/json",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
        },
    )
    assert should_forward(flow) is False


def test_same_site_json_get_is_forwarded():
    flow = _flow(
        host="example.com",
        path="/api/account",
        headers={
            "accept": "application/json",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        },
    )
    with patch("backend.proxy.filter_requests.custom_blacklist_matches", return_value=False), patch(
        "backend.proxy.filter_requests.is_noise", return_value=False
    ):
        assert should_forward(flow) is True


def test_google_ad_background_host_is_not_forwarded():
    flow = _flow(
        host="ep2.adtrafficquality.google",
        path="/sodar/sodar2/254/runner.html",
        headers={"sec-fetch-dest": "iframe", "sec-fetch-mode": "navigate"},
    )
    assert should_forward(flow) is False


def test_prefetch_navigation_is_not_forwarded():
    flow = _flow(
        headers={
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-purpose": "prefetch",
        },
    )
    with patch("backend.proxy.filter_requests.custom_blacklist_matches", return_value=False):
        assert should_forward(flow) is False
