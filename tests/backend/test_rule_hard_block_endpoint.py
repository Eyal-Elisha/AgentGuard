"""PATCH /rules/<code>/hard-block is admin-only, and it persists.

Granting a rule the right to hard block gives it a veto over every other signal
on the page, so it sits behind `require_admin` rather than the plain `require_jwt`
the enabled toggle uses. These tests hold that line, and check the value survives
`rule_sync_metadata`, which runs on every request a rule takes part in and used
to overwrite this column from the catalogue.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet

from backend import create_app
from backend.auth import hash_password, issue_token
from backend.storage import sqlite_store as store

_RULE = {
    "rule_code": "demo_rule",
    "weight": 0.2,
    "rule_type": "deterministic",
    "compute_class": "cheap",
    "is_enabled": True,
    "is_hard_block": False,
    "description": "A rule used only by this test",
}


class TestRuleHardBlockEndpoint(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self._old_env = {
            key: os.environ.get(key)
            for key in ("DATABASE_URL", "JWT_SECRET", "REQUIRE_AUTH",
                        "AGENTGUARD_LOG_ENCRYPTION_KEY")
        }
        db_path = Path(os.path.join(self.temp_dir.name, "test.db")).resolve().as_posix()
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["JWT_SECRET"] = "test-secret"
        os.environ["REQUIRE_AUTH"] = "true"
        os.environ["AGENTGUARD_LOG_ENCRYPTION_KEY"] = Fernet.generate_key().decode("utf-8")

        self.app = create_app()
        self.client = self.app.test_client()

        store.user_create("bob", hash_password("bob-pass"), is_admin=False)
        store.user_create("admin", hash_password("admin-pass"), is_admin=True)
        with self.app.app_context():
            self.user_token = issue_token(1, "bob", False)
            self.admin_token = issue_token(2, "admin", True)

        self.client.post("/rules", json=_RULE, headers=self._auth(self.admin_token))

    def tearDown(self) -> None:
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    @staticmethod
    def _auth(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def _patch(self, token: str, value: bool):
        return self.client.patch(
            f"/rules/{_RULE['rule_code']}/hard-block",
            json={"is_hard_block": value},
            headers=self._auth(token),
        )

    def test_admin_can_turn_hard_block_on(self):
        response = self._patch(self.admin_token, True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["is_hard_block"])
        self.assertTrue(store.rule_get(_RULE["rule_code"])["is_hard_block"])

    def test_admin_can_turn_it_off_again(self):
        self._patch(self.admin_token, True)
        response = self._patch(self.admin_token, False)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["is_hard_block"])

    def test_a_normal_user_is_refused(self):
        response = self._patch(self.user_token, True)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(store.rule_get(_RULE["rule_code"])["is_hard_block"])

    def test_an_anonymous_caller_is_refused(self):
        response = self.client.patch(
            f"/rules/{_RULE['rule_code']}/hard-block", json={"is_hard_block": True},
        )
        self.assertEqual(response.status_code, 401)

    def test_a_missing_rule_is_a_404(self):
        response = self.client.patch(
            "/rules/no_such_rule/hard-block",
            json={"is_hard_block": True},
            headers=self._auth(self.admin_token),
        )
        self.assertEqual(response.status_code, 404)

    def test_a_non_boolean_is_rejected(self):
        response = self.client.patch(
            f"/rules/{_RULE['rule_code']}/hard-block",
            json={"is_hard_block": "yes"},
            headers=self._auth(self.admin_token),
        )
        self.assertEqual(response.status_code, 400)

    def test_the_catalogue_sync_no_longer_overwrites_the_choice(self):
        """The setting has to survive the next request the rule takes part in.

        `rule_sync_metadata` runs then, and while it still owns weight and
        description it must leave this column alone, or an admin's decision
        would last only until the next page was analysed.
        """
        self._patch(self.admin_token, True)

        store.rule_sync_metadata(
            rule_code=_RULE["rule_code"],
            weight=0.9,
            rule_type="deterministic",
            compute_class="cheap",
            description="rewritten by the catalogue",
        )

        refreshed = store.rule_get(_RULE["rule_code"])
        self.assertTrue(refreshed["is_hard_block"], "the admin's choice was overwritten")
        self.assertEqual(refreshed["weight"], 0.9, "the catalogue still owns the weight")


if __name__ == "__main__":
    unittest.main()
