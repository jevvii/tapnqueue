"""
Legacy shim for staff_admin.py.
Delegates to tapnque.ui.staff.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tapnque.ui.staff import StaffAdmin, main

if __name__ == "__main__":
    main()
