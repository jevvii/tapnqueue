"""
Legacy shim for admin_auth.py.
Delegates to tapnque.core.auth.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tapnque.config import AUTH_FILE_PATH as AUTH_FILE
from tapnque.core.auth import (
    DEFAULT_USERS,
    _build_user,
    _hash_password,
    authenticate,
    ensure_auth_file,
    load_users,
    require_admin_login,
)

__all__ = [
    "AUTH_FILE",
    "DEFAULT_USERS",
    "_build_user",
    "_hash_password",
    "authenticate",
    "ensure_auth_file",
    "load_users",
    "require_admin_login",
]
