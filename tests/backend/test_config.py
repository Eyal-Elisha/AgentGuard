import os
import tempfile
import unittest
from pathlib import Path

from backend import create_app
from backend.auth import issue_token


class ConfigTestCase(unittest.TestCase):
    def test_create_app_requires_jwt_secret(self):
        """``create_app`` always resolves ``JWT_SECRET`` (login issues JWTs even when REQUIRE_AUTH is off)."""
        old_env = {
            "DATABASE_URL": os.environ.get("DATABASE_URL"),
            "JWT_SECRET": os.environ.get("JWT_SECRET"),
            "REQUIRE_AUTH": os.environ.get("REQUIRE_AUTH"),
        }
        try:
            os.environ.pop("JWT_SECRET", None)
            os.environ["REQUIRE_AUTH"] = "true"
            os.environ["DATABASE_URL"] = "sqlite:///:memory:"

            with self.assertRaises(RuntimeError):
                create_app()
        finally:
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_require_auth_protects_api_routes(self):
        old_env = {
            "DATABASE_URL": os.environ.get("DATABASE_URL"),
            "JWT_SECRET": os.environ.get("JWT_SECRET"),
            "REQUIRE_AUTH": os.environ.get("REQUIRE_AUTH"),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                db_url_path = Path(temp_dir, "test.db").resolve().as_posix()
                os.environ["DATABASE_URL"] = f"sqlite:///{db_url_path}"
                os.environ["JWT_SECRET"] = "test-secret"
                os.environ["REQUIRE_AUTH"] = "true"

                app = create_app()
                client = app.test_client()

                unauthorized = client.get("/sessions")
                self.assertEqual(unauthorized.status_code, 401)

                with app.app_context():
                    token = issue_token(1, "alice", False)

                authorized = client.get("/sessions", headers={"Authorization": f"Bearer {token}"})
                self.assertEqual(authorized.status_code, 200)
                self.assertEqual(authorized.get_json(), [])
            finally:
                for key, value in old_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    def test_health_route_is_public(self):
        old_env = {
            "DATABASE_URL": os.environ.get("DATABASE_URL"),
            "JWT_SECRET": os.environ.get("JWT_SECRET"),
            "REQUIRE_AUTH": os.environ.get("REQUIRE_AUTH"),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                db_url_path = Path(temp_dir, "test.db").resolve().as_posix()
                os.environ["DATABASE_URL"] = f"sqlite:///{db_url_path}"
                os.environ["JWT_SECRET"] = "test-secret"
                os.environ["REQUIRE_AUTH"] = "true"

                app = create_app()
                client = app.test_client()

                response = client.get("/health")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json(), {"status": "ok"})
            finally:
                for key, value in old_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
