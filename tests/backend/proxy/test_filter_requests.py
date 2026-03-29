"""Custom blacklist must override EasyPrivacy noise (see filter_requests.should_forward)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from backend.proxy.filter_requests import should_forward


def _flow(host: str = "www.monkeytype.com", ua: str = "Mozilla/5.0 Chrome/120.0.0.0") -> SimpleNamespace:
    req = SimpleNamespace(
        method="GET",
        host=host,
        pretty_url=f"https://{host}/",
        headers={"user-agent": ua},
        content=b"",
    )
    return SimpleNamespace(request=req)


def test_custom_blacklist_match_forces_forward_even_when_noise():
    with patch("backend.proxy.filter_requests.flow_matches_custom_blacklist", return_value=True), patch(
        "backend.proxy.filter_requests.is_noise", return_value=True
    ):
        assert should_forward(_flow()) is True


def test_noise_skips_when_not_on_custom_blacklist():
    with patch("backend.proxy.filter_requests.flow_matches_custom_blacklist", return_value=False), patch(
        "backend.proxy.filter_requests.is_noise", return_value=True
    ):
        assert should_forward(_flow()) is False


def test_browser_get_request_is_forwarded_when_not_noise():
    with patch("backend.proxy.filter_requests.flow_matches_custom_blacklist", return_value=False), patch(
        "backend.proxy.filter_requests.is_noise", return_value=False
    ):
        assert should_forward(_flow()) is True


def test_non_browser_request_is_not_forwarded():
    with patch("backend.proxy.filter_requests.is_noise", return_value=False):
        assert should_forward(_flow(ua="curl/8.0.1")) is False
