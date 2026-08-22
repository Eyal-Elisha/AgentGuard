"""Custom blacklist entries still enforce without flooding backend analysis."""

from __future__ import annotations

from unittest.mock import patch

from backend.custom_blacklist import custom_blacklist_matches
from backend.proxy.filter_requests import should_forward
from tests.backend.proxy.test_filter_requests import _flow


def test_custom_blacklist_match_forces_forward_even_when_noise():
    with patch("backend.proxy.filter_requests.custom_blacklist_matches", return_value=True), patch(
        "backend.proxy.filter_requests.is_noise", return_value=True
    ):
        assert should_forward(_flow()) is True


def test_static_custom_blacklist_match_is_not_forwarded_for_audit():
    with patch("backend.proxy.filter_requests.custom_blacklist_matches", return_value=True):
        # _flow defaults to a navigation, so a subresource has to override every
        # navigation marker: dest alone still leaves mode=navigate behind.
        flow = _flow(
            path="/favicon.ico",
            headers={"sec-fetch-dest": "image", "sec-fetch-mode": "no-cors", "accept": "*/*"},
        )
        assert should_forward(flow) is False


def test_background_custom_blacklist_match_is_not_forwarded_for_audit():
    flow = _flow(
        host="blocked.example.test",
        headers={"accept": "*/*", "sec-fetch-mode": "cors", "sec-fetch-dest": "empty"},
    )
    with patch("backend.proxy.filter_requests.custom_blacklist_matches", return_value=True), patch(
        "backend.proxy.filter_requests.is_relevant_for_analysis", return_value=False
    ):
        assert should_forward(flow) is False


def test_blacklisted_meaningful_action_is_forwarded():
    flow = _flow(
        host="blocked.example.test",
        path="/login",
        method="POST",
        headers={
            "content-type": "application/x-www-form-urlencoded",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
        },
    )
    with patch("backend.proxy.filter_requests.custom_blacklist_matches", return_value=True):
        assert should_forward(flow) is True


def test_shared_custom_blacklist_matcher_handles_subdomains():
    assert custom_blacklist_matches(
        "www.youtube.com",
        "https://www.youtube.com/watch?v=123",
        frozenset({"youtube.com"}),
    ) is True
