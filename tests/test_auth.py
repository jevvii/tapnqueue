"""
Unit tests for TapNQue Authentication Module.
Verifies hashing, salting, and credential validation.
"""

import json
import tempfile
import unittest
from pathlib import Path

from tapnque.core.auth import _build_user, _hash_password, authenticate, ensure_auth_file


class TestAuth(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.auth_file = Path(self.temp_dir.name) / "test_admin_users.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_build_user_salting(self):
        """Verify each build_user call produces a distinct random salt."""
        u1 = _build_user("admin", "secret123")
        u2 = _build_user("admin", "secret123")
        self.assertNotEqual(u1["salt"], u2["salt"])
        self.assertNotEqual(u1["password_hash"], u2["password_hash"])

    def test_default_auth_file_generation(self):
        """Verify ensure_auth_file creates default staff and super_admin users."""
        self.assertFalse(self.auth_file.exists())
        ensure_auth_file(self.auth_file)
        self.assertTrue(self.auth_file.exists())

        users = json.loads(self.auth_file.read_text(encoding="utf-8"))
        self.assertIn("staff", users)
        self.assertIn("super_admin", users)

    def test_authentication_success_and_failure(self):
        """Verify authentication checks username and password hashes correctly."""
        ensure_auth_file(self.auth_file)

        # Default credentials
        self.assertTrue(authenticate("staff", "staff", "staff123", self.auth_file))
        self.assertTrue(authenticate("super_admin", "admin", "admin123", self.auth_file))

        # Wrong password
        self.assertFalse(authenticate("staff", "staff", "wrongpassword", self.auth_file))
        # Wrong username
        self.assertFalse(authenticate("staff", "intruder", "staff123", self.auth_file))
        # Wrong role
        self.assertFalse(authenticate("super_admin", "staff", "staff123", self.auth_file))
        # Nonexistent role
        self.assertFalse(authenticate("guest", "guest", "guest", self.auth_file))


if __name__ == "__main__":
    unittest.main()
