"""
Legacy shim for main_launcher.py.
Delegates to tapnque.ui.launcher.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tapnque.ui.launcher import MainLauncher, main

if __name__ == "__main__":
    main()
