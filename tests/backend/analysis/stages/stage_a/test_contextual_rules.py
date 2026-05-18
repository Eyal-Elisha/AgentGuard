"""Unit tests for Stage A contextual rules.

Each rule produces a continuous score = min(N / Nmax, 1) over a `SessionContext`
constructed in-memory (no DB, no proxy plumbing).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.analysis.rules import PriorEvent, SessionContext
from backend.analysis.stages.stage_a.contextual_rules import (
    rule_previously_warned_domain_in_session,
    rule_redirect_to_sensitive_action,
    rule_repeated_sensitive_action_after_warning,
    rule_sensitive_action_frequency_spike,
)


T0 = datetime(2026, 5, 17, 10, 0, 0, tzinfo=timezone.utc)


def _ev(seconds_before: float, host: str, action: str, score: float = 0.0) -> PriorEvent:
    return PriorEvent(
        timestamp=T0 - timedelta(seconds=seconds_before),
        host=host,
        guard_action=action,
        risk_score=score,
    )


# ---------------------------------------------------------------------------
# Rule 1 — Sensitive Action Frequency Spike
# ---------------------------------------------------------------------------

class TestRuleSensitiveActionFrequencySpike:
    config = {"Nmax": 5, "T_ms": 60_000}

    def test_empty_session_is_skipped(self):
        session = SessionContext(current_event_timestamp=T0, current_event_host="x.com")
        score, explanation = rule_sensitive_action_frequency_spike(session, self.config)
        assert score is None
        assert "Skipped" in explanation

    def test_no_timestamp_is_skipped(self):
        session = SessionContext(prior_events=[_ev(10, "a.com", "Warn")])
        score, _ = rule_sensitive_action_frequency_spike(session, self.config)
        assert score is None

    def test_window_with_no_flagged_events_scores_zero(self):
        # Session has prior data, so the rule applies and a 0 count is meaningful.
        prior = [_ev(10, "a.com", "Allow"), _ev(20, "b.com", "Allow")]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="x.com",
            prior_events=prior,
        )
        score, _ = rule_sensitive_action_frequency_spike(session, self.config)
        assert score == 0.0

    def test_counts_only_flagged_in_window(self):
        prior = [
            _ev(10, "a.com", "Warn"),
            _ev(20, "a.com", "Allow"),
            _ev(30, "b.com", "Block"),
            _ev(120, "c.com", "Warn"),
        ]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="x.com",
            prior_events=prior,
        )
        score, explanation = rule_sensitive_action_frequency_spike(session, self.config)
        assert score == pytest.approx(2 / 5)
        assert "2" in explanation

    def test_saturates_at_one(self):
        prior = [_ev(i, f"h{i}.com", "Warn") for i in range(1, 11)]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="x.com",
            prior_events=prior,
        )
        score, _ = rule_sensitive_action_frequency_spike(session, self.config)
        assert score == 1.0

    def test_inclusive_window_lower_bound(self):
        prior = [_ev(60, "a.com", "Warn")]  # exactly t0 - 60s with T_ms=60_000
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="x.com",
            prior_events=prior,
        )
        score, _ = rule_sensitive_action_frequency_spike(session, self.config)
        assert score == pytest.approx(1 / 5)

    def test_excludes_outside_window(self):
        # 2 minutes ago, window is 60s; session is non-empty so rule applies
        # and returns 0 (not skipped).
        prior = [_ev(120, "a.com", "Warn")]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="x.com",
            prior_events=prior,
        )
        score, _ = rule_sensitive_action_frequency_spike(session, self.config)
        assert score == 0.0


# ---------------------------------------------------------------------------
# Rule 2 — Repeated Sensitive Action After Warning
# ---------------------------------------------------------------------------

class TestRuleRepeatedSensitiveActionAfterWarning:
    config = {"Nmax": 5}

    def test_no_prior_warning_is_skipped(self):
        prior = [_ev(10, "a.com", "Allow")]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="x.com",
            prior_events=prior,
        )
        score, explanation = rule_repeated_sensitive_action_after_warning(
            session, self.config
        )
        assert score is None
        assert "Skipped" in explanation

    def test_counts_flagged_after_first_warning(self):
        prior = [
            _ev(60, "a.com", "Warn"),   # first warning
            _ev(50, "b.com", "Allow"),
            _ev(40, "c.com", "Warn"),
            _ev(30, "d.com", "Block"),
            _ev(20, "e.com", "Allow"),
        ]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="x.com",
            prior_events=prior,
        )
        score, explanation = rule_repeated_sensitive_action_after_warning(
            session, self.config
        )
        assert score == pytest.approx(2 / 5)
        assert "2" in explanation

    def test_first_warning_itself_not_counted(self):
        # The first warning establishes t_warn; nothing happens after it,
        # so the rule applies (anchor exists) and returns 0.
        prior = [_ev(30, "a.com", "Warn")]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="x.com",
            prior_events=prior,
        )
        score, _ = rule_repeated_sensitive_action_after_warning(session, self.config)
        assert score == 0.0

    def test_saturates_at_one(self):
        prior = [_ev(60, "a.com", "Warn")] + [
            _ev(60 - i, f"h{i}.com", "Warn") for i in range(1, 11)
        ]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="x.com",
            prior_events=prior,
        )
        score, _ = rule_repeated_sensitive_action_after_warning(session, self.config)
        assert score == 1.0


# ---------------------------------------------------------------------------
# Rule 3 — Redirect to Sensitive Action
# ---------------------------------------------------------------------------

class TestRuleRedirectToSensitiveAction:
    config = {"Nmax": 5, "redirect_window_ms": 2_000}

    def test_empty_session_is_skipped(self):
        session = SessionContext(current_event_timestamp=T0, current_event_host="x.com")
        score, explanation = rule_redirect_to_sensitive_action(session, self.config)
        assert score is None
        assert "Skipped" in explanation

    def test_no_link_in_window_is_skipped(self):
        prior = [
            PriorEvent(
                timestamp=T0 - timedelta(seconds=10),
                host="far.com",
                guard_action="Allow",
                risk_score=0.0,
            )
        ]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="x.com",
            prior_events=prior,
        )
        score, _ = rule_redirect_to_sensitive_action(session, self.config)
        assert score is None

    def test_single_same_domain_redirect(self):
        prior = [
            PriorEvent(
                timestamp=T0 - timedelta(milliseconds=500),
                host="x.com",
                guard_action="Allow",
                risk_score=0.0,
            )
        ]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="x.com",
            prior_events=prior,
        )
        score, explanation = rule_redirect_to_sensitive_action(session, self.config)
        assert score == pytest.approx(1 / 5)
        assert "1 fast hop" in explanation

    def test_single_cross_domain_redirect(self):
        prior = [
            PriorEvent(
                timestamp=T0 - timedelta(milliseconds=500),
                host="evil.com",
                guard_action="Allow",
                risk_score=0.0,
            )
        ]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="bank.com",
            prior_events=prior,
        )
        score, _ = rule_redirect_to_sensitive_action(session, self.config)
        assert score == pytest.approx(2 / 5)

    def test_chain_breaks_outside_window(self):
        # prior_events are stored ASCending by timestamp (oldest first), as
        # produced by the session loader.
        prior = [
            PriorEvent(
                timestamp=T0 - timedelta(milliseconds=10_000),
                host="hop1.com",
                guard_action="Allow",
                risk_score=0.0,
            ),
            PriorEvent(
                timestamp=T0 - timedelta(milliseconds=500),
                host="hop2.com",
                guard_action="Allow",
                risk_score=0.0,
            ),
        ]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="bank.com",
            prior_events=prior,
        )
        score, _ = rule_redirect_to_sensitive_action(session, self.config)
        # hop1 is too far back; only the hop2 -> bank cross-domain hop counts.
        assert score == pytest.approx(2 / 5)

    def test_full_cross_domain_chain_saturates(self):
        gaps_ms = [500, 1_000, 1_500, 2_000, 1_800, 1_200]
        prior: list[PriorEvent] = []
        cumulative = 0
        for i, gap in enumerate(gaps_ms):
            cumulative += gap
            prior.insert(
                0,
                PriorEvent(
                    timestamp=T0 - timedelta(milliseconds=cumulative),
                    host=f"hop{i}.com",
                    guard_action="Allow",
                    risk_score=0.0,
                ),
            )
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="bank.com",
            prior_events=prior,
        )
        score, explanation = rule_redirect_to_sensitive_action(session, self.config)
        assert score == 1.0
        assert "arrived here through" in explanation
        assert "fast hops" in explanation


# ---------------------------------------------------------------------------
# Rule 4 — Previously Warned Domain in Session
# ---------------------------------------------------------------------------

class TestRulePreviouslyWarnedDomainInSession:
    config = {"Nmax": 5}

    def test_empty_session_is_skipped(self):
        session = SessionContext(current_event_timestamp=T0, current_event_host="x.com")
        score, explanation = rule_previously_warned_domain_in_session(session, self.config)
        assert score is None
        assert "Skipped" in explanation

    def test_no_warned_domains_is_skipped(self):
        prior = [_ev(30, "a.com", "Allow"), _ev(20, "b.com", "Allow")]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="a.com",
            prior_events=prior,
        )
        score, _ = rule_previously_warned_domain_in_session(session, self.config)
        assert score is None

    def test_counts_revisits_to_warned_domain(self):
        prior = [
            _ev(60, "evil.com", "Warn"),  # warning establishes evil.com in W
            _ev(50, "evil.com", "Allow"),  # 1st revisit
            _ev(40, "good.com", "Allow"),  # ignored
            _ev(30, "evil.com", "Allow"),  # 2nd revisit
        ]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="other.com",
            prior_events=prior,
        )
        score, explanation = rule_previously_warned_domain_in_session(
            session, self.config
        )
        # The original warning event + 2 revisits = 3 prior events with host in W
        assert score == pytest.approx(3 / 5)
        assert "3" in explanation

    def test_current_host_is_warned_adds_one(self):
        prior = [
            _ev(60, "evil.com", "Warn"),
            _ev(50, "good.com", "Allow"),
        ]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="evil.com",
            prior_events=prior,
        )
        score, _ = rule_previously_warned_domain_in_session(session, self.config)
        # 1 prior event with host in W + 1 for current host
        assert score == pytest.approx(2 / 5)

    def test_block_also_counts_as_warning(self):
        prior = [_ev(30, "blocked.com", "Block")]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="blocked.com",
            prior_events=prior,
        )
        score, _ = rule_previously_warned_domain_in_session(session, self.config)
        assert score == pytest.approx(2 / 5)

    def test_saturates_at_one(self):
        prior = [_ev(60, "evil.com", "Warn")] + [
            _ev(50 - i, "evil.com", "Allow") for i in range(10)
        ]
        session = SessionContext(
            current_event_timestamp=T0,
            current_event_host="other.com",
            prior_events=prior,
        )
        score, _ = rule_previously_warned_domain_in_session(session, self.config)
        assert score == 1.0
