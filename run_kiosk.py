"""
Launch Student Kiosk directly
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tapnque.ui.kiosk import main

if __name__ == "__main__":
    main()
