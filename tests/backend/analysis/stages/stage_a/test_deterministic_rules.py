"""Unit tests for Stage A deterministic rules (Rules 1–9).

Each rule is tested with at least:
  - A triggering case  → score == 1.0
  - A non-triggering case → score == 0.0

Rule 1 (domain blacklist) mocks the external API so no network calls are made.
"""

import pytest
from unittest.mock import patch

from helpers import (
    make_features,
    HTML_PASSWORD_FORM,
    HTML_CREDIT_CARD_FORM,
    HTML_BENIGN,
    HTML_PAYPAL_TITLE,
    HTML_META_REFRESH_EXTERNAL,
    HTML_JS_REDIRECT_EXTERNAL,
    HTML_EXTERNAL_FORM_ACTION,
)
from backend.analysis.stages.stage_a.deterministic_rules import (
    rule_domain_blacklist,
    rule_unencrypted_connection,
    rule_sensitive_fields,
    rule_brand_domain_mismatch,
    rule_unexpected_redirect,
    rule_external_form_action,
    rule_typosquatting,
    rule_ip_based_url,
    rule_custom_blacklist,
)


# ---------------------------------------------------------------------------
# Rule 1 — Domain in Popular Blacklist
# ---------------------------------------------------------------------------

class TestRuleDomainBlacklist:
    _MOCK = "backend.analysis.stages.stage_a.deterministic_rules.blacklist_cache.is_listed"

    def test_listed_domain_triggers(self):
        features = make_features("https://evil-phish.com/login")
        with patch(self._MOCK, return_value=(True, "PhishTank")) as mock:
            score, explanation = rule_domain_blacklist(features)
        assert score == 1.0
        assert "PhishTank" in explanation

    def test_unlisted_domain_passes(self):
        features = make_features("https://example.com/page")
        with patch(self._MOCK, return_value=(False, "not listed")):
            score, _ = rule_domain_blacklist(features)
        assert score == 0.0

    def test_subdomain_checks_parent(self):
        """Should check 'evil.com' when visiting 'login.evil.com'."""
        features = make_features("https://login.evil.com/auth")
        calls = []

        def fake_is_listed(domain):
            calls.append(domain)
            return (True, "URLhaus") if domain == "evil.com" else (False, "not listed")

        with patch(self._MOCK, side_effect=fake_is_listed):
            score, _ = rule_domain_blacklist(features)

        assert score == 1.0
        assert "evil.com" in calls

    def test_api_unavailable_fails_open(self):
        """If the API is unavailable the rule must not block."""
        features = make_features("https://example.com")
        with patch(self._MOCK, return_value=(False, "URLhaus unavailable")):
            score, _ = rule_domain_blacklist(features)
        assert score == 0.0


# ---------------------------------------------------------------------------
# Rule 2 — Unencrypted Connection
# ---------------------------------------------------------------------------

class TestRuleUnencryptedConnection:
    def test_http_always_triggers(self):
        features = make_features("http://example.com/page", HTML_BENIGN)
        score, explanation = rule_unencrypted_connection(features)
        assert score == 1.0
        assert "http" in explanation.lower()

    def test_http_with_no_sensitive_fields_still_triggers(self):
        """HTTP should block regardless of whether sensitive fields are present."""
        features = make_features("http://example.com", HTML_BENIGN)
        score, _ = rule_unencrypted_connection(features)
        assert score == 1.0

    def test_https_passes(self):
        features = make_features("https://example.com/login", HTML_PASSWORD_FORM)
        score, _ = rule_unencrypted_connection(features)
        assert score == 0.0

    def test_https_no_html_passes(self):
        features = make_features("https://api.example.com/data")
        score, _ = rule_unencrypted_connection(features)
        assert score == 0.0


# ---------------------------------------------------------------------------
# Rule 3 — Sensitive Fields Present
# ---------------------------------------------------------------------------

class TestRuleSensitiveFields:
    def test_password_input_triggers(self):
        features = make_features("https://example.com/login", HTML_PASSWORD_FORM)
        score, explanation = rule_sensitive_fields(features)
        assert score == 1.0
        assert "credential" in explanation.lower() or "sensitive" in explanation.lower()

    def test_credit_card_fields_trigger(self):
        features = make_features("https://shop.com/pay", HTML_CREDIT_CARD_FORM)
        score, _ = rule_sensitive_fields(features)
        assert score == 1.0

    def test_no_form_passes(self):
        features = make_features("https://example.com", HTML_BENIGN)
        score, _ = rule_sensitive_fields(features)
        assert score == 0.0

    def test_non_sensitive_form_passes(self):
        html = """<html><body>
          <form><input type="text" name="search"><input type="submit"></form>
        </body></html>"""
        features = make_features("https://example.com/search", html)
        score, _ = rule_sensitive_fields(features)
        assert score == 0.0

    def test_api_key_field_triggers(self):
        html = """<html><body>
          <form><input type="text" name="api_key"></form>
        </body></html>"""
        features = make_features("https://example.com", html)
        score, _ = rule_sensitive_fields(features)
        assert score == 1.0

    def test_otp_field_triggers(self):
        html = """<html><body>
          <form><input type="text" name="otp"></form>
        </body></html>"""
        features = make_features("https://example.com", html)
        score, _ = rule_sensitive_fields(features)
        assert score == 1.0


# ---------------------------------------------------------------------------
# Rule 4 — Brand Domain Mismatch
# ---------------------------------------------------------------------------

class TestRuleBrandDomainMismatch:
    def test_paypal_title_on_wrong_domain_triggers(self):
        features = make_features("https://paypal-login.evil.com", HTML_PAYPAL_TITLE)
        score, explanation = rule_brand_domain_mismatch(features)
        assert score == 1.0
        assert "paypal" in explanation.lower()

    def test_paypal_title_on_official_domain_passes(self):
        features = make_features("https://www.paypal.com/signin", HTML_PAYPAL_TITLE)
        score, _ = rule_brand_domain_mismatch(features)
        assert score == 0.0

    def test_no_brand_in_title_passes(self):
        features = make_features("https://example.com", HTML_BENIGN)
        score, _ = rule_brand_domain_mismatch(features)
        assert score == 0.0

    def test_google_title_on_wrong_domain_triggers(self):
        html = "<html><head><title>Google Account Login</title></head><body></body></html>"
        features = make_features("https://google-accounts.fake.com", html)
        score, explanation = rule_brand_domain_mismatch(features)
        assert score == 1.0
        assert "google" in explanation.lower()

    def test_no_dom_passes(self):
        features = make_features("https://example.com")  # no HTML body
        score, _ = rule_brand_domain_mismatch(features)
        assert score == 0.0


# ---------------------------------------------------------------------------
# Rule 5 — Unexpected Redirect During Sensitive Interaction
# ---------------------------------------------------------------------------

class TestRuleUnexpectedRedirect:
    def test_meta_refresh_to_external_triggers(self):
        features = make_features("https://bank.com/login", HTML_META_REFRESH_EXTERNAL)
        score, explanation = rule_unexpected_redirect(features)
        assert score == 1.0
        assert "meta-refresh" in explanation.lower() or "evil.com" in explanation

    def test_js_location_redirect_to_external_triggers(self):
        features = make_features("https://bank.com/login", HTML_JS_REDIRECT_EXTERNAL)
        score, explanation = rule_unexpected_redirect(features)
        assert score == 1.0
        assert "evil.com" in explanation

    def test_no_sensitive_fields_passes(self):
        """Redirect on a page with no sensitive fields should not trigger."""
        html = """<html><head>
          <meta http-equiv="refresh" content="0; url=https://other.com">
        </head><body><p>Hello</p></body></html>"""
        features = make_features("https://example.com", html)
        score, _ = rule_unexpected_redirect(features)
        assert score == 0.0

    def test_same_domain_redirect_passes(self):
        html = """<html><head>
          <meta http-equiv="refresh" content="0; url=https://bank.com/dashboard">
        </head><body><form><input type="password" name="password"></form></body></html>"""
        features = make_features("https://bank.com/login", html)
        score, _ = rule_unexpected_redirect(features)
        assert score == 0.0

    def test_onerror_redirect_triggers(self):
        html = """<html><body>
          <form><input type="password" name="password"></form>
          <img src="x" onerror="window.location = 'https://evil.com/steal'">
        </body></html>"""
        features = make_features("https://bank.com/login", html)
        score, explanation = rule_unexpected_redirect(features)
        assert score == 1.0
        assert "evil.com" in explanation


# ---------------------------------------------------------------------------
# Rule 6 — External Form Action
# ---------------------------------------------------------------------------

class TestRuleExternalFormAction:
    def test_sensitive_form_to_external_host_triggers(self):
        features = make_features("https://bank.com/login", HTML_EXTERNAL_FORM_ACTION)
        score, explanation = rule_external_form_action(features)
        assert score == 1.0
        assert "evil.com" in explanation

    def test_sensitive_form_to_same_host_passes(self):
        features = make_features("https://bank.com/login", HTML_PASSWORD_FORM)
        score, _ = rule_external_form_action(features)
        assert score == 0.0

    def test_non_sensitive_form_to_external_passes(self):
        html = """<html><body>
          <form action="https://other.com/search">
            <input type="text" name="q">
          </form>
        </body></html>"""
        features = make_features("https://example.com", html)
        score, _ = rule_external_form_action(features)
        assert score == 0.0

    def test_no_dom_passes(self):
        features = make_features("https://example.com")
        score, _ = rule_external_form_action(features)
        assert score == 0.0


# ---------------------------------------------------------------------------
# Rule 7 — Typosquatting
# ---------------------------------------------------------------------------

class TestRuleTyposquatting:
    def test_digit_substitution_triggers(self):
        """paypa1.com is a typosquat of paypal.com"""
        features = make_features("https://paypa1.com/login")
        score, explanation = rule_typosquatting(features)
        assert score == 1.0
        assert "paypa1.com" in explanation or "paypal" in explanation.lower()

    def test_character_swap_triggers(self):
        """payal.com (missing p) is a typosquat of paypal.com"""
        features = make_features("https://payal.com/login")
        score, _ = rule_typosquatting(features)
        assert score == 1.0

    def test_official_domain_passes(self):
        features = make_features("https://paypal.com/login")
        score, _ = rule_typosquatting(features)
        assert score == 0.0

    def test_unrelated_domain_passes(self):
        features = make_features("https://completely-different-xyz.com")
        score, _ = rule_typosquatting(features)
        assert score == 0.0

    def test_ip_address_skipped(self):
        features = make_features("https://192.168.1.1/login")
        score, explanation = rule_typosquatting(features)
        assert score == 0.0
        assert "ip address" in explanation.lower()

    def test_cyrillic_homoglyph_triggers(self):
        """pаypal.com with Cyrillic 'а' should be detected."""
        features = make_features("https://p\u0430ypal.com/login")  # Cyrillic а
        score, _ = rule_typosquatting(features)
        assert score == 1.0


# ---------------------------------------------------------------------------
# Rule 8 — IP Based URL
# ---------------------------------------------------------------------------

class TestRuleIpBasedUrl:
    def test_ipv4_triggers(self):
        features = make_features("http://192.168.1.100/login")
        score, explanation = rule_ip_based_url(features)
        assert score == 1.0
        assert "192.168.1.100" in explanation

    def test_public_ipv4_triggers(self):
        features = make_features("https://203.0.113.5/pay")
        score, _ = rule_ip_based_url(features)
        assert score == 1.0

    def test_registered_domain_passes(self):
        features = make_features("https://example.com")
        score, _ = rule_ip_based_url(features)
        assert score == 0.0


# ---------------------------------------------------------------------------
# Rule 9 — Custom Local Blacklist
# ---------------------------------------------------------------------------

class TestRuleCustomBlacklist:
    def test_domain_in_blacklist_triggers(self):
        features = make_features("https://blocked-site.com/login")
        score, explanation = rule_custom_blacklist(
            features, frozenset({"blocked-site.com"})
        )
        assert score == 1.0
        assert "blacklist" in explanation.lower()

    def test_url_in_blacklist_triggers(self):
        features = make_features("https://example.com/bad-path")
        score, _ = rule_custom_blacklist(
            features, frozenset({"https://example.com/bad-path"})
        )
        assert score == 1.0

    def test_domain_not_in_blacklist_passes(self):
        features = make_features("https://safe-site.com")
        score, _ = rule_custom_blacklist(features, frozenset({"blocked-site.com"}))
        assert score == 0.0

    def test_empty_blacklist_passes(self):
        features = make_features("https://example.com")
        score, _ = rule_custom_blacklist(features, frozenset())
        assert score == 0.0

    def test_none_blacklist_passes(self):
        features = make_features("https://example.com")
        score, _ = rule_custom_blacklist(features, None)
        assert score == 0.0
