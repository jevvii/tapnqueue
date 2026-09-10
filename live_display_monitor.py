"""
Legacy shim for live_display_monitor.py.
Delegates to tapnque.ui.monitor.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tapnque.ui.monitor import LiveDisplayMonitor, TicketCard, main

if __name__ == "__main__":
    main()
