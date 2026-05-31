import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend import create_app
from backend.auth import decode_token, hash_password, issue_token
from backend.storage import sqlite_store as store
from backend.storage.sqlite_store import UsernameTakenError

from backend_api_test_base import BackendApiTestCase


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

    def test_signup_duplicate_username_returns_400(self):
        first = self.client.post("/signup", json={"username": "dupuser", "password": "a"})
        second = self.client.post("/signup", json={"username": "dupuser", "password": "b"})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(second.get_json()["error"], "Username already exists")

    def test_user_create_duplicate_raises_username_taken(self):
        store.user_create("race-user", hash_password("x"), False)
        with self.assertRaises(UsernameTakenError):
            store.user_create("race-user", hash_password("y"), False)

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

    def test_historical_events_can_be_queried_by_user_and_risk(self):
        alice_id = store.user_create("alice-events", hash_password("alice-pass"), False)
        bob_id = store.user_create("bob-events", hash_password("bob-pass"), False)
        timestamp = datetime(2026, 3, 25, 12, 0, tzinfo=timezone.utc)
        alice_session_id = store.session_create(alice_id, timestamp, "test", "agent-a")
        bob_session_id = store.session_create(bob_id, timestamp, "test", "agent-b")

        alice_event_id = store.event_create(
            alice_session_id,
            timestamp,
            "https://example.test/alice-high",
            "Warn",
            0.82,
            "GET",
            "{}",
        )
        store.event_create(
            alice_session_id,
            timestamp,
            "https://example.test/alice-low",
            "Allow",
            0.15,
            "GET",
            "{}",
        )
        store.event_create(
            bob_session_id,
            timestamp,
            "https://example.test/bob-high",
            "Block",
            0.95,
            "POST",
            "{}",
        )

        response = self.client.get(
            "/events",
            query_string={"user_id": str(alice_id), "min_risk_score": "0.7"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["event_id"], alice_event_id)
        self.assertEqual(body[0]["session_id"], alice_session_id)
        self.assertEqual(body[0]["user_id"], alice_id)

        invalid_user = self.client.get("/events", query_string={"user_id": "not-an-id"})
        self.assertEqual(invalid_user.status_code, 400)
        self.assertEqual(invalid_user.get_json()["error"], "Invalid user_id")

    def test_second_close_returns_409(self):
        session_id = self.create_session().get_json()["session_id"]
        first = self.client.post(f"/sessions/{session_id}/close")
        second = self.client.post(f"/sessions/{session_id}/close")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.get_json()["error"], "Session is already closed")

    def test_validation_and_empty_result_behaviors(self):
        empty_sessions = self.client.get("/sessions")
        self.assertEqual(empty_sessions.status_code, 200)
        self.assertEqual(empty_sessions.get_json(), [])

        bad_session = self.create_session(environment="staging")
        self.assertEqual(bad_session.status_code, 400)
        self.assertEqual(bad_session.get_json()["error"], "Invalid environment value")

        missing_event = self.client.get("/events/999")
        self.assertEqual(missing_event.status_code, 404)
        self.assertEqual(missing_event.get_json()["error"], "Event not found")

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


class SessionDeleteAuthorizationTestCase(unittest.TestCase):
    """DELETE /sessions/:id requires admin when REQUIRE_AUTH is enabled."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        self._old_env = {
            "DATABASE_URL": os.environ.get("DATABASE_URL"),
            "JWT_SECRET": os.environ.get("JWT_SECRET"),
            "REQUIRE_AUTH": os.environ.get("REQUIRE_AUTH"),
        }
        db_url_path = Path(self.db_path).resolve().as_posix()
        os.environ["DATABASE_URL"] = f"sqlite:///{db_url_path}"
        os.environ["JWT_SECRET"] = "test-secret"
        os.environ["REQUIRE_AUTH"] = "true"

        self.app = create_app()
        self.client = self.app.test_client()

        store.user_create("bob", hash_password("bob-pass"), is_admin=False)
        store.user_create("admin", hash_password("admin-pass"), is_admin=True)

        with self.app.app_context():
            self.bob_token = issue_token(1, "bob", False)
            self.admin_token = issue_token(2, "admin", True)
            self.session_id = store.session_create(
                1,
                datetime(2026, 3, 25, 12, 0, tzinfo=timezone.utc),
                "test",
                "agent-1",
            )

    def tearDown(self) -> None:
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    def test_non_admin_cannot_delete_session(self):
        response = self.client.delete(
            f"/sessions/{self.session_id}",
            headers={"Authorization": f"Bearer {self.bob_token}"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"], "Forbidden")
        self.assertIsNotNone(store.session_get(self.session_id))

    def test_admin_can_delete_any_session(self):
        response = self.client.delete(
            f"/sessions/{self.session_id}",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["message"], "Session deleted successfully")
        self.assertIsNone(store.session_get(self.session_id))
