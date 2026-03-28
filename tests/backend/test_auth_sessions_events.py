from backend.auth import decode_token
from backend.storage import sqlite_store as store

from tests.backend.backend_api_test_base import BackendApiTestCase


class AuthSessionsEventsTestCase(BackendApiTestCase):
    def test_signup_login_and_authenticated_session_creation(self):
        signup = self.client.post("/signup", json={"username": "alice", "password": "s3cr3t"})
        self.assertEqual(signup.status_code, 201)
        self.assertEqual(signup.get_json()["user_id"], 1)

        login = self.client.post("/login", json={"username": "alice", "password": "s3cr3t"})
        self.assertEqual(login.status_code, 200)
        token = login.get_json()["jwt"]

        with self.app.app_context():
            payload = decode_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], "1")
        self.assertEqual(payload["username"], "alice")
        self.assertFalse(payload["is_admin"])

        session = self.client.post(
            "/sessions",
            json={
                "start_time": "2026-03-25T12:00:00Z",
                "agent_name": "agent-1",
                "environment": "test",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(session.status_code, 201)
        session_id = session.get_json()["session_id"]

        stored = store.session_get(session_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored["user_id"], 1)

    def test_invalid_bearer_token_is_rejected_for_session_creation(self):
        response = self.client.post(
            "/sessions",
            json={
                "start_time": "2026-03-25T12:00:00Z",
                "agent_name": "agent-1",
                "environment": "test",
            },
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "Unauthorized")

    def test_session_events_global_events_and_stats(self):
        session = self.create_session()
        self.assertEqual(session.status_code, 201)
        session_id = session.get_json()["session_id"]

        first = self.create_event(
            session_id,
            url="https://example.test/allow",
            timestamp="2026-03-25T12:00:00Z",
            guard_action="Allow",
            risk_score=0.25,
        )
        second = self.create_event(
            session_id,
            url="https://example.test/warn",
            timestamp="2026-03-25T12:05:00Z",
            guard_action="Warn",
            risk_score=0.8,
            method="POST",
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        second_event_id = second.get_json()["event_id"]

        filtered = self.client.get(
            f"/sessions/{session_id}/events",
            query_string={"guard_action": "Warn", "min_risk_score": "0.7"},
        )
        self.assertEqual(filtered.status_code, 200)
        filtered_body = filtered.get_json()
        self.assertEqual(len(filtered_body), 1)
        self.assertEqual(filtered_body[0]["event_id"], second_event_id)
        self.assertNotIn("session_id", filtered_body[0])

        global_events = self.client.get(
            "/events",
            query_string={"guard_action": "Warn", "from_timestamp": "2026-03-25T12:01:00Z"},
        )
        self.assertEqual(global_events.status_code, 200)
        global_body = global_events.get_json()
        self.assertEqual(len(global_body), 1)
        self.assertEqual(global_body[0]["session_id"], session_id)
        self.assertEqual(global_body[0]["event_id"], second_event_id)

        event_detail = self.client.get(f"/events/{second_event_id}")
        self.assertEqual(event_detail.status_code, 200)
        self.assertEqual(event_detail.get_json()["url"], "https://example.test/warn")

        stats = self.client.get(f"/sessions/{session_id}/events/stats")
        self.assertEqual(stats.status_code, 200)
        body = stats.get_json()
        self.assertEqual(body["total_events"], 2)
        self.assertEqual(body["allow"], 1)
        self.assertEqual(body["warn"], 1)
        self.assertEqual(body["block"], 0)
        self.assertAlmostEqual(body["average_risk_score"], 0.525)

    def test_validation_and_empty_result_behaviors(self):
        empty_sessions = self.client.get("/sessions")
        self.assertEqual(empty_sessions.status_code, 200)
        self.assertEqual(empty_sessions.get_json(), [])

        bad_session = self.create_session(environment="staging")
        self.assertEqual(bad_session.status_code, 400)
        self.assertEqual(bad_session.get_json()["error"], "Invalid environment value")

        missing_event = self.client.get("/events/999")
        self.assertEqual(missing_event.status_code, 404)

        bad_filters = self.client.get("/events", query_string={"min_risk_score": "not-a-number"})
        self.assertEqual(bad_filters.status_code, 400)
        self.assertEqual(bad_filters.get_json()["error"], "Invalid query parameters")

        reversed_range = self.client.get(
            "/events",
            query_string={"from_timestamp": "2026-03-25T12:05:00Z", "to_timestamp": "2026-03-25T12:01:00Z"},
        )
        self.assertEqual(reversed_range.status_code, 400)
        self.assertEqual(reversed_range.get_json()["error"], "Invalid query parameters")

        session_id = self.create_session().get_json()["session_id"]
        out_of_bounds_risk = self.create_event(session_id=session_id, risk_score=1.5)
        self.assertEqual(out_of_bounds_risk.status_code, 400)
        self.assertEqual(out_of_bounds_risk.get_json()["error"], "Invalid payload: risk_score")
