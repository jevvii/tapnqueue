"""
TapNQue Main Launcher Entrypoint
"""

import os
import sys
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tapnque.ui.launcher import main

if __name__ == "__main__":
    main()
