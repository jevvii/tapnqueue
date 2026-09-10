"""
Legacy shim for live_display.py.
Delegates to tapnque.ui.live_display.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tapnque.ui.live_display import LiveDisplay, main

if __name__ == "__main__":
    main()