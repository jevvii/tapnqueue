"""
TapNQue Core Module
Contains database, authentication, and fundamental business logic.
"""

from .database import DatabaseManager, get_database
from .auth import require_admin_login, authenticate, ensure_auth_file

__all__ = [
    "DatabaseManager",
    "get_database",
    "require_admin_login",
    "authenticate",
    "ensure_auth_file",
]
