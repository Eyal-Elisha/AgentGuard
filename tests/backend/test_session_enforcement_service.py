from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

from backend.analysis.rules import Decision
from backend.session_enforcement.service import enforce_session_risk
from backend.session_risk.models import SessionRiskSummary


class TestSessionEnforcementService(TestCase):
    def test_enforce_session_risk_does_not_upgrade_allow_to_warn(self):
        summary = SessionRiskSummary(
            session_risk_score=0.86,
            risk_level="elevated",
            should_stop=False,
            stop_reason=None,
            highest_event_risk=0.86,
            recent_weighted_risk=0.86,
            risky_event_count=1,
            warn_count=1,
            block_count=0,
            sensitive_interaction_count=0,
            hard_block_count=0,
            risk_trend="up",
            average_risk_score=0.86,
        )

        with patch("backend.session_enforcement.service.calculate_session_risk", return_value=summary):
            enforcement = enforce_session_risk(
                session_id=1,
                timestamp=datetime.utcnow(),
                current_decision=Decision.ALLOW,
            )

        self.assertEqual(enforcement.decision, Decision.ALLOW)
        self.assertEqual(enforcement.level, "warn")
        self.assertEqual(enforcement.reason, "Session risk is elevated; risk score is 0.86.")
