"""
Legacy shim for database_manager.py.
Delegates to tapnque.core.database.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tapnque.core.database import DatabaseManager, get_database

__all__ = ["DatabaseManager", "get_database"]
