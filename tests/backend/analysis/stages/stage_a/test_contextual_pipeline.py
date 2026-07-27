"""Contextual-rules pipeline integration tests.

No ngrok, no proxy, no web server — everything runs in-process.

The trick:
  1. Build `ExtractedFeatures` directly (skip the HTML parser) so we control
     exactly which deterministic rules fire and keep the initial score inside
     the ambiguous zone [0.25, 0.70] that triggers contextual evaluation.
  2. Build `SessionContext` in-memory with crafted `PriorEvent` lists that
     represent the history we want to test.
  3. Run `StageAEvaluator().evaluate(features, session)` and assert on
     individual rule results and the final decision.

Run with:
    pytest tests/backend/analysis/stages/stage_a/test_contextual_pipeline.py -v
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from backend.analysis.rules import Decision, PriorEvent, SessionContext
from backend.analysis.stages.stage_a import StageAEvaluator
from backend.feature_extraction.feature_extractor import (
    DomFeatures,
    ExtractedFeatures,
    FormDetails,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BLACKLIST_MOCK = "backend.analysis.stages.stage_a.deterministic_rules.blacklist_cache.is_listed"
_NOT_LISTED = (False, "not listed")

T0 = datetime(2026, 5, 17, 10, 0, 0, tzinfo=timezone.utc)


def _ev(seconds_before: float, host: str, action: str) -> PriorEvent:
    return PriorEvent(
        timestamp=T0 - timedelta(seconds=seconds_before),
        host=host,
        guard_action=action,
        risk_score=0.4,
    )


def _ambiguous_features(
    url: str = "https://login-test-portal.com/verify",
    host: str = "login-test-portal.com",
    form_action_host: str = "data.collect.io",
) -> ExtractedFeatures:
    """Return features that produce a deterministic score in [0.25, 0.70].

    Triggers (no hard-block):
      - brand_domain_mismatch  (weight 0.15): "PayPal" in title on non-paypal.com
      - sensitive_fields        (weight 0.10): password input
      - external_form_action    (weight 0.10): form posts to a different host
      - unexpected_redirect     (weight 0.10): meta-refresh to an external host
        during a sensitive interaction

    Weighted score ≈ 0.45 / 1.50 ≈ 0.30, safely inside the ambiguous zone.
    """
    return ExtractedFeatures(
        url=url,
        host=host,
        scheme="https",
        headers={"content-type": "text/html; charset=utf-8"},
        is_html=True,
        raw_body=(
            '<html><head>'
            '<meta http-equiv="refresh" content="0; url=https://redirect-collector.io/next">'
            '</head><body>PayPal verify account password</body></html>'
        ),
        dom=DomFeatures(
            page_title="PayPal – Verify Your Account",
            all_text_content="PayPal verify account password",
            forms=[
                FormDetails(
                    action=f"https://{form_action_host}/submit",
                    method="post",
                    action_host=form_action_host,
                    inputs=[
                        {"type": "text", "name": "username", "id": "user"},
                        {"type": "password", "name": "password", "id": "pass"},
                    ],
                )
            ],
        ),
    )


def _get_rule(result, rule_id: str):
    return next((r for r in result.rule_results if r.rule_id == rule_id), None)


# ---------------------------------------------------------------------------
# Baseline: deterministic score lands in the ambiguous zone
# ---------------------------------------------------------------------------

class TestAmbiguousBaseline:
    def test_deterministic_score_is_in_ambiguous_zone(self):
        """Sanity-check: our crafted features produce a score that triggers contextual rules."""
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features())

        assert not result.hard_block_triggered
        assert 0.25 <= result.risk_score < 0.70, (
            f"Expected deterministic score in [0.25, 0.70], got {result.risk_score}"
        )

    def test_no_session_contextual_rules_all_skip(self):
        """Without session history every contextual rule must return score=None (skipped)."""
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features(), session)

        contextual_ids = {
            "sensitive_action_frequency_spike",
            "repeated_sensitive_action_after_warning",
            "redirect_to_sensitive_action",
            "previously_warned_domain_in_session",
        }
        for rule_id in contextual_ids:
            r = _get_rule(result, rule_id)
            assert r is not None, f"Rule {rule_id} missing from results"
            assert r.score is None, f"{rule_id}: expected None (skipped), got {r.score}"


# ---------------------------------------------------------------------------
# Rule 1 — Sensitive Action Frequency Spike
# ---------------------------------------------------------------------------

class TestFrequencySpikeIntegration:
    def test_no_flagged_events_score_is_zero(self):
        """Frequency spike is 0 when prior events are all Allow."""
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
            prior_events=[
                _ev(10, "login-test-portal.com", "Allow"),
                _ev(20, "login-test-portal.com", "Allow"),
            ],
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features(), session)

        r = _get_rule(result, "sensitive_action_frequency_spike")
        assert r is not None
        assert r.score == 0.0
        assert not r.triggered

    def test_flagged_events_raise_score(self):
        """Three Warn events within 60 s → score = 3/5 = 0.60."""
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
            prior_events=[
                _ev(5, "login-test-portal.com", "Warn"),
                _ev(15, "login-test-portal.com", "Warn"),
                _ev(30, "login-test-portal.com", "Warn"),
            ],
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features(), session)

        r = _get_rule(result, "sensitive_action_frequency_spike")
        assert r is not None
        assert r.score == pytest.approx(0.60)
        assert r.triggered
        assert result.risk_score > 0.29  # context pushed the score up

    def test_saturates_at_one(self):
        """Five or more flagged events within 60 s → frequency spike score capped at 1.0."""
        # Events ordered oldest-first (largest seconds_before first), matching DB ordering.
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
            prior_events=[_ev(i * 5, "login-test-portal.com", "Warn") for i in range(5, 0, -1)],
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features(), session)

        r = _get_rule(result, "sensitive_action_frequency_spike")
        assert r.score == 1.0
        assert r.triggered
        # Risk score is a weighted average over all rules (many score 0), so final
        # score won't hit BLOCK threshold just from contextual rules alone.
        assert result.risk_score > 0.30

    def test_events_outside_window_ignored(self):
        """Flagged events older than 60 s must not count."""
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
            prior_events=[
                _ev(90, "login-test-portal.com", "Warn"),   # outside 60 s window
                _ev(120, "login-test-portal.com", "Block"),  # outside 60 s window
            ],
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features(), session)

        r = _get_rule(result, "sensitive_action_frequency_spike")
        assert r.score == 0.0


# ---------------------------------------------------------------------------
# Rule 2 — Repeated Sensitive Action After Warning
# ---------------------------------------------------------------------------

class TestRepeatedAfterWarningIntegration:
    def test_no_prior_warning_rule_skips(self):
        """Rule must be skipped when no Warn/Block event exists in history."""
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
            prior_events=[_ev(30, "login-test-portal.com", "Allow")],
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features(), session)

        r = _get_rule(result, "repeated_sensitive_action_after_warning")
        assert r.score is None

    def test_post_warning_events_raise_score(self):
        """Two Warn events after the first warning → score = 2/5 = 0.40."""
        first_warn_ts = T0 - timedelta(seconds=120)
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
            prior_events=[
                PriorEvent(timestamp=first_warn_ts, host="login-test-portal.com",
                           guard_action="Warn", risk_score=0.4),
                _ev(60, "login-test-portal.com", "Warn"),
                _ev(30, "login-test-portal.com", "Warn"),
            ],
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features(), session)

        r = _get_rule(result, "repeated_sensitive_action_after_warning")
        assert r.score == pytest.approx(0.40)
        assert r.triggered


# ---------------------------------------------------------------------------
# Rule 3 — Redirect to Sensitive Action
# ---------------------------------------------------------------------------

class TestRedirectToSensitiveActionIntegration:
    def test_no_chain_rule_skips(self):
        """Rule skips when prior events are outside the 2-second redirect window."""
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
            prior_events=[_ev(30, "google.com", "Allow")],  # 30 s gap → no chain
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features(), session)

        r = _get_rule(result, "redirect_to_sensitive_action")
        assert r.score is None

    def test_same_domain_hop_scores_one_per_link(self):
        """Two same-domain events within 2 s → chain_links=2, n_redirect=2, score=2/5=0.40.

        Events must be in oldest-first order (matching DB ASC ordering) so that
        reversed() in the rule processes them newest-first.
        """
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
            prior_events=[
                _ev(1.0, "login-test-portal.com", "Allow"),  # older
                _ev(0.5, "login-test-portal.com", "Allow"),  # newer
            ],
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features(), session)

        r = _get_rule(result, "redirect_to_sensitive_action")
        assert r is not None
        assert r.score == pytest.approx(0.40)

    def test_cross_domain_hop_scores_two_per_link(self):
        """One cross-domain hop within 2 s → n_redirect=2 → score=2/5=0.40."""
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
            prior_events=[_ev(1.0, "tracking.evil.io", "Allow")],
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features(), session)

        r = _get_rule(result, "redirect_to_sensitive_action")
        assert r is not None
        assert r.score == pytest.approx(0.40)

    def test_chain_break_stops_counting(self):
        """A gap > 2 s breaks the chain; only events within the unbroken window count.

        Events are oldest-first so reversed() processes newest-to-oldest correctly.
        """
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
            prior_events=[
                _ev(60, "hop2.io", "Allow"),    # older — breaks chain before this
                _ev(1.0, "hop1.io", "Allow"),   # newer — within 2 s of T0, counts
            ],
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features(), session)

        r = _get_rule(result, "redirect_to_sensitive_action")
        assert r is not None
        # Only hop1.io was in the unbroken window (cross-domain → n_redirect=2 → 2/5=0.40)
        assert r.score == pytest.approx(0.40)


# ---------------------------------------------------------------------------
# Rule 4 — Previously Warned Domain in Session
# ---------------------------------------------------------------------------

class TestPreviouslyWarnedDomainIntegration:
    def test_no_warned_domains_rule_skips(self):
        """Rule skips when no prior event was flagged."""
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
            prior_events=[_ev(60, "safe.example.com", "Allow")],
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features(), session)

        r = _get_rule(result, "previously_warned_domain_in_session")
        assert r.score is None

    def test_revisit_to_warned_domain_scores(self):
        """Current host previously warned → score = 2/5 = 0.40 (1 prior + 1 current)."""
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
            prior_events=[
                _ev(120, "login-test-portal.com", "Warn"),
                _ev(60,  "login-test-portal.com", "Allow"),
            ],
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features(), session)

        r = _get_rule(result, "previously_warned_domain_in_session")
        assert r is not None
        assert r.score > 0.0
        assert r.triggered

    def test_different_warned_domain_also_counts(self):
        """Prior Warn on a different host still populates W; current visit raises score."""
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
            prior_events=[
                _ev(120, "phish.io", "Warn"),
                _ev(60,  "phish.io", "Allow"),
            ],
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features(), session)

        r = _get_rule(result, "previously_warned_domain_in_session")
        # phish.io is in W; 2 prior visits to phish.io (1 Warn + 1 Allow)
        assert r is not None
        assert r.score > 0.0


# ---------------------------------------------------------------------------
# Compound scenario: multiple contextual rules fire together
# ---------------------------------------------------------------------------

class TestCompoundContextualScenario:
    def test_combined_signals_push_decision_to_warn(self):
        """When frequency spike + previously-warned-domain both fire, the combined
        score is meaningfully higher than the no-context baseline."""
        # 4 Warn events in last 60 s AND current host was previously warned.
        # Oldest-first so reversed() in redirect rule processes correctly.
        prior = [_ev(i * 8, "login-test-portal.com", "Warn") for i in range(4, 0, -1)]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
            prior_events=prior,
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            result = StageAEvaluator().evaluate(_ambiguous_features(), session)

        spike = _get_rule(result, "sensitive_action_frequency_spike")
        warned = _get_rule(result, "previously_warned_domain_in_session")
        assert spike.triggered
        assert warned.triggered
        # Final score is a weighted average over all rules (most score 0), so
        # it won't hit BLOCK but should be materially above the no-context baseline.
        assert result.risk_score > 0.33
        assert result.decision in (Decision.WARN, Decision.BLOCK)

    def test_baseline_vs_with_context_score_increases(self):
        """Demonstrate the core value: context raises the risk score."""
        features = _ambiguous_features()

        # No context
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            baseline = StageAEvaluator().evaluate(features)

        # With 3 recent Warn events on the same host
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="login-test-portal.com",
            prior_events=[_ev(i * 10, "login-test-portal.com", "Warn") for i in range(1, 4)],
        )
        with patch(_BLACKLIST_MOCK, return_value=_NOT_LISTED):
            with_context = StageAEvaluator().evaluate(features, session)

        assert with_context.risk_score > baseline.risk_score, (
            f"Context should raise score: {baseline.risk_score:.3f} → {with_context.risk_score:.3f}"
        )
