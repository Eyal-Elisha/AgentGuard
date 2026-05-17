from unittest import TestCase
from unittest.mock import Mock, patch

from backend.analysis.rules import Decision
from backend.proxy.decision_client import fetch_backend_decision


class ProxyDecisionClientTestCase(TestCase):
    def test_block_reason_includes_event_and_session_context(self):
        with patch("backend.proxy.decision_client.requests.Session") as session_cls:
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "decision": "block",
                "session_enforcement": {
                    "level": "warn",
                    "reason": "Session risk is elevated; risk score is 0.86.",
                },
                "evaluation": {
                    "decision": "block",
                    "rule_results": [
                        {
                            "rule_id": "custom_blacklist",
                            "triggered": True,
                            "hard_block": True,
                            "explanation": "URL matches the custom local blacklist",
                        },
                    ],
                },
            }
            session = Mock()
            session.post.return_value = response
            session_cls.return_value = session

            decision = fetch_backend_decision({"url": "https://blocked.test"})

        self.assertEqual(decision.decision, Decision.BLOCK)
        self.assertTrue(decision.reason.startswith("AgentGuard blocked"))
        self.assertIn("custom local blacklist", decision.reason)
        self.assertIn("Session context:", decision.reason)
        self.assertIn("Session risk is elevated", decision.reason)

    def test_closed_session_context_does_not_replace_block_reason(self):
        with patch("backend.proxy.decision_client.requests.Session") as session_cls:
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "decision": "block",
                "session_enforcement": {
                    "level": "closed",
                    "reason": "There is no active proxy session.",
                },
                "evaluation": None,
            }
            session = Mock()
            session.post.return_value = response
            session_cls.return_value = session

            decision = fetch_backend_decision({"url": "https://blocked.test"})

        self.assertEqual(decision.decision, Decision.BLOCK)
        self.assertIn("AgentGuard blocked the request", decision.reason)
        self.assertIn("Session context:", decision.reason)
        self.assertIn("There is no active proxy session", decision.reason)
