"""
Legacy shim for super_admin.py.
Delegates to tapnque.ui.super_admin.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tapnque.ui.super_admin import SuperAdmin, StatCard, main

if __name__ == "__main__":
    main()
