"""Integration tests — Stage A evaluated against real fetched pages.

These tests make actual HTTP requests and are skipped in normal CI runs.
Run them explicitly with:

    pytest -m integration
    pytest -m integration -v

Each test documents WHY the expected decision is correct so failures are
easy to diagnose if a site changes its content.
"""

import pytest
import requests

from unittest.mock import patch

from helpers import make_features_from_url
from backend.analysis.stages.stage_a import StageAEvaluator
from backend.analysis.rules import Decision

_BLACKLIST_MOCK = "backend.analysis.stages.stage_a.deterministic_rules.blacklist_cache.is_listed"
_NOT_LISTED = (False, "not listed")

pytestmark = pytest.mark.integration


def _evaluate(url: str, **evaluator_kwargs) -> "EvaluationResult":
    features = make_features_from_url(url)
    with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
        return StageAEvaluator(**evaluator_kwargs).evaluate(features)


def _skip_if_unreachable(url: str):
    try:
        requests.head(url, timeout=5, allow_redirects=False)
    except requests.RequestException:
        pytest.skip(f"Host unreachable: {url}")


# ---------------------------------------------------------------------------
# Clean HTTPS pages — expected: ALLOW
# ---------------------------------------------------------------------------

class TestCleanSites:
    def test_google_homepage(self):
        """google.com is a well-known HTTPS site with no sensitive fields — should ALLOW."""
        _skip_if_unreachable("https://www.google.com")
        result = _evaluate("https://www.google.com")
        assert result.decision == Decision.ALLOW
        assert not result.hard_block_triggered

    def test_example_com(self):
        """example.com is a benign HTTPS placeholder — should ALLOW."""
        _skip_if_unreachable("https://example.com")
        result = _evaluate("https://example.com")
        assert result.decision == Decision.ALLOW

    def test_github_homepage(self):
        """github.com is an official domain — brand mismatch rule must not fire."""
        _skip_if_unreachable("https://github.com")
        result = _evaluate("https://github.com")
        brand_result = next(r for r in result.rule_results if r.rule_id == "brand_domain_mismatch")
        assert brand_result.score == 0.0


# ---------------------------------------------------------------------------
# HTTP pages — expected: BLOCK (Rule 2 hard block)
# ---------------------------------------------------------------------------

class TestHttpSites:
    def test_http_example_com(self):
        """Any HTTP connection must hard-block regardless of page content."""
        _skip_if_unreachable("http://example.com")
        result = _evaluate("http://example.com")
        assert result.decision == Decision.BLOCK
        assert result.hard_block_triggered
        unencrypted = next(r for r in result.rule_results if r.rule_id == "unencrypted_connection")
        assert unencrypted.score == 1.0

    def test_http_httpbin(self):
        """httpbin.org serves over HTTP — must hard-block."""
        _skip_if_unreachable("http://httpbin.org/html")
        result = _evaluate("http://httpbin.org/html")
        assert result.decision == Decision.BLOCK
        assert result.hard_block_triggered


# ---------------------------------------------------------------------------
# IP-based URLs — expected: Rule 8 triggers, risk score > 0
# ---------------------------------------------------------------------------

class TestIpUrls:
    def test_public_dns_ip(self):
        """Accessing a page via a raw IP (1.1.1.1) should trigger Rule 8."""
        _skip_if_unreachable("https://1.1.1.1")
        result = _evaluate("https://1.1.1.1")
        ip_result = next(r for r in result.rule_results if r.rule_id == "ip_based_url")
        assert ip_result.score == 1.0
        assert ip_result.triggered


# ---------------------------------------------------------------------------
# Custom blacklist — expected: BLOCK regardless of page content
# ---------------------------------------------------------------------------

class TestCustomBlacklist:
    def test_safe_site_blocked_by_custom_list(self):
        """A normally-safe site added to the custom blacklist must be hard-blocked."""
        _skip_if_unreachable("https://example.com")
        result = _evaluate("https://example.com", custom_blacklist=frozenset({"example.com"}))
        assert result.decision == Decision.BLOCK
        assert result.hard_block_triggered
        custom = next(r for r in result.rule_results if r.rule_id == "custom_blacklist")
        assert custom.score == 1.0


# ---------------------------------------------------------------------------
# Official brand on their own domain — expected: brand rule must NOT fire
# ---------------------------------------------------------------------------

class TestOfficialBrandPages:
    def test_paypal_on_official_domain(self):
        """PayPal's own login page should not trigger brand domain mismatch."""
        _skip_if_unreachable("https://www.paypal.com/signin")
        result = _evaluate("https://www.paypal.com/signin")
        brand_result = next(r for r in result.rule_results if r.rule_id == "brand_domain_mismatch")
        assert brand_result.score == 0.0

    def test_microsoft_on_official_domain(self):
        """Microsoft's own page should not trigger brand domain mismatch."""
        _skip_if_unreachable("https://www.microsoft.com")
        result = _evaluate("https://www.microsoft.com")
        brand_result = next(r for r in result.rule_results if r.rule_id == "brand_domain_mismatch")
        assert brand_result.score == 0.0
