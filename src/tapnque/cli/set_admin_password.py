"""
Update staff or super admin credentials securely.

Usage:
    python -m tapnque.cli.set_admin_password <role> <username> <password>
    python set_admin_password.py <role> <username> <password>

Roles:
    staff, super_admin
"""

import json
import sys

from tapnque.config import AUTH_FILE_PATH
from tapnque.core.auth import _build_user, ensure_auth_file

VALID_ROLES = {"staff", "super_admin"}


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in VALID_ROLES:
        roles = ", ".join(sorted(VALID_ROLES))
        raise SystemExit(
            "Usage: python -m tapnque.cli.set_admin_password <role> <username> <password>\n"
            f"Roles: {roles}\n"
            "Example: python -m tapnque.cli.set_admin_password staff counter1 myStrongPassword123"
        )

    role, username, password = sys.argv[1], sys.argv[2], sys.argv[3]
    clean_username = username.strip()
    if not clean_username or not password:
        raise SystemExit("Username and password cannot be empty.")

    ensure_auth_file(AUTH_FILE_PATH)
    try:
        users = json.loads(AUTH_FILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        users = {}

    users[role] = _build_user(clean_username, password)
    AUTH_FILE_PATH.write_text(json.dumps(users, indent=2), encoding="utf-8")
    print(f"✓ Successfully updated '{role}' credentials for user '{clean_username}'.")


if __name__ == "__main__":
    main()
