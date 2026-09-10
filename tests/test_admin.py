import time
import unittest
from hashlib import sha256
from unittest.mock import patch

from fastapi import HTTPException

from backend.app.api import routes_admin


class AdminSessionTests(unittest.TestCase):
    def tearDown(self):
        with routes_admin._lock:
            routes_admin._sessions.clear()

    def test_logout_revokes_active_session(self):
        token = "test-admin-session"
        with routes_admin._lock:
            routes_admin._sessions[token] = time.time() + 60

        self.assertEqual(routes_admin.logout(token), {"ended": True})
        with routes_admin._lock:
            self.assertNotIn(token, routes_admin._sessions)

    def test_login_session_and_logout_lifecycle(self):
        password = "acceptance-admin-password"
        with (
            patch.object(routes_admin.settings, "admin_email", "admin@example.test"),
            patch.object(routes_admin.settings, "admin_password_hash", sha256(password.encode()).hexdigest()),
        ):
            response = routes_admin.login(routes_admin.Login(email="ADMIN@example.test", password=password))

        token = response["access_token"]
        self.assertEqual(routes_admin.admin_session(f"Bearer {token}"), token)
        self.assertEqual(routes_admin.logout(token), {"ended": True})
        with self.assertRaises(HTTPException) as rejected:
            routes_admin.admin_session(f"Bearer {token}")
        self.assertEqual(rejected.exception.status_code, 401)

    def test_invalid_admin_credentials_are_rejected(self):
        with (
            patch.object(routes_admin.settings, "admin_email", "admin@example.test"),
            patch.object(routes_admin.settings, "admin_password_hash", sha256(b"correct-password").hexdigest()),
        ):
            with self.assertRaises(HTTPException) as rejected:
                routes_admin.login(routes_admin.Login(email="admin@example.test", password="incorrect-password"))
        self.assertEqual(rejected.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
