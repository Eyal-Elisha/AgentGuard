"""Custom blacklist entries always reach enforcement."""

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


def test_static_custom_blacklist_match_is_forwarded_for_enforcement():
    with patch("backend.proxy.filter_requests.custom_blacklist_matches", return_value=True):
        flow = _flow(path="/favicon.ico", headers={"sec-fetch-dest": "image"})
        assert should_forward(flow) is True


def test_custom_blacklist_bypasses_relevance_filter():
    flow = _flow(host="monkeytype.com", headers={"accept": "*/*", "sec-fetch-mode": "cors"})
    with patch("backend.proxy.filter_requests.is_relevant_for_analysis", return_value=False):
        assert should_forward(flow) is True


def test_shared_custom_blacklist_matcher_handles_subdomains():
    assert custom_blacklist_matches(
        "www.youtube.com",
        "https://www.youtube.com/watch?v=123",
        frozenset({"youtube.com"}),
    ) is True
