"""Integration tests for StageAEvaluator.

Verifies the full pipeline: FeatureExtractor → ExtractedFeatures → StageAEvaluator → EvaluationResult.
"""

import pytest
from unittest.mock import patch

from backend.feature_extraction.feature_extractor import FeatureExtractor
from backend.analysis.stages.stage_a import StageAEvaluator
from backend.analysis.rules import Decision

from helpers import (
    make_features,
    HTML_PASSWORD_FORM,
    HTML_BENIGN,
    HTML_PAYPAL_TITLE,
    HTML_EXTERNAL_FORM_ACTION,
)

_BLACKLIST_MOCK = "backend.analysis.stages.stage_a.deterministic_rules.blacklist_cache.is_listed"


class TestStageAEvaluatorPipeline:
    """Verify ExtractedFeatures flows correctly into the evaluator."""

    def test_feature_extractor_output_is_accepted(self):
        """StageAEvaluator.evaluate() must accept FeatureExtractor output without error."""
        extractor = FeatureExtractor()
        features = extractor.extract(
            url="https://example.com/page",
            method="GET",
            headers={"content-type": "text/html"},
            body=HTML_BENIGN.encode(),
        )
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(features)

        assert result is not None
        assert result.decision in list(Decision)
        assert 0.0 <= result.risk_score <= 1.0
        assert len(result.rule_results) > 0

    def test_result_has_entry_for_every_rule(self):
        """Every deterministic rule should produce a RuleResult (triggered or skipped)."""
        from backend.analysis.rules import DETERMINISTIC_RULES

        features = make_features("https://example.com", HTML_BENIGN)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(features)

        rule_ids = {r.rule_id for r in result.rule_results}
        expected_ids = {r.rule_id for r in DETERMINISTIC_RULES}
        assert rule_ids == expected_ids


class TestStageADecisions:
    """Verify correct ALLOW / WARN / BLOCK decisions for known scenarios."""

    def test_clean_https_page_is_allowed(self):
        features = make_features("https://example.com", HTML_BENIGN)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(features)
        assert result.decision == Decision.ALLOW
        assert not result.hard_block_triggered

    def test_http_page_is_hard_blocked(self):
        """Any HTTP connection must result in a BLOCK (hard block on Rule 2)."""
        features = make_features("http://example.com/login", HTML_PASSWORD_FORM)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(features)
        assert result.decision == Decision.BLOCK
        assert result.hard_block_triggered
        assert result.risk_score == 1.0

    def test_blacklisted_domain_is_hard_blocked(self):
        features = make_features("https://phishing-site.com/login", HTML_PASSWORD_FORM)
        with patch(_BLACKLIST_MOCK, return_value=(True, "PhishTank")):
            result = StageAEvaluator().evaluate(features)
        assert result.decision == Decision.BLOCK
        assert result.hard_block_triggered

    def test_hard_block_skips_remaining_rules(self):
        """After a hard block, all subsequent rules must have score=None."""
        features = make_features("https://phishing-site.com/login")
        with patch(_BLACKLIST_MOCK, return_value=(True, "PhishTank")):
            result = StageAEvaluator().evaluate(features)

        triggered = next(r for r in result.rule_results if r.rule_id == "domain_blacklist")
        assert triggered.score == 1.0

        skipped = [r for r in result.rule_results if r.score is None]
        assert len(skipped) > 0

    def test_custom_blacklist_hard_blocks(self):
        features = make_features("https://internal-blocked.com/login")
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator(
                custom_blacklist=frozenset({"internal-blocked.com"})
            ).evaluate(features)
        assert result.decision == Decision.BLOCK
        assert result.hard_block_triggered

    def test_typosquat_is_hard_blocked(self):
        features = make_features("https://paypa1.com/login", HTML_PASSWORD_FORM)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(features)
        assert result.decision == Decision.BLOCK
        assert result.hard_block_triggered

    def test_brand_mismatch_with_sensitive_fields_raises_score(self):
        """Brand mismatch + sensitive fields should produce a non-zero risk score."""
        features = make_features("https://paypal-fake.com/login", HTML_PAYPAL_TITLE)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(features)
        assert result.risk_score > 0.0

    def test_external_form_action_raises_score(self):
        features = make_features("https://bank.com/login", HTML_EXTERNAL_FORM_ACTION)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(features)
        assert result.risk_score > 0.0

    def test_multiple_soft_signals_raise_score(self):
        """Brand mismatch + sensitive fields should produce a non-zero risk score."""
        features = make_features("https://paypal-fake.com/login", HTML_PAYPAL_TITLE)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(features)
        # Both brand_domain_mismatch and sensitive_fields should have fired
        triggered = [r.rule_id for r in result.rule_results if r.triggered]
        assert "brand_domain_mismatch" in triggered
        assert "sensitive_fields" in triggered
        assert result.risk_score > 0.0

    def test_ip_based_url_raises_score(self):
        features = make_features("https://203.0.113.5/login", HTML_PASSWORD_FORM)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(features)
        assert result.risk_score > 0.0
