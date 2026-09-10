"""
Launch Super Admin Operations Console directly
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tapnque.ui.super_admin import main

if __name__ == "__main__":
    main()
