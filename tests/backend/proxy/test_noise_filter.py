from __future__ import annotations

from unittest.mock import patch

from backend.proxy.filters.noise.easyprivacy import _host_matches_easyprivacy


def test_easyprivacy_matches_exact_domain_and_subdomains_only():
    with patch(
        "backend.proxy.filters.noise.easyprivacy.EASYPRIVACY_DOMAINS",
        {"tracker.example.com"},
    ):
        assert _host_matches_easyprivacy("tracker.example.com") is True
        assert _host_matches_easyprivacy("cdn.tracker.example.com") is True
        assert _host_matches_easyprivacy("mytracker.example.com") is False
