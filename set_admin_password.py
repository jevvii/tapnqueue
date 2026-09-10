"""
Legacy shim for set_admin_password.py.
Delegates to tapnque.cli.set_admin_password.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tapnque.cli.set_admin_password import main

if __name__ == "__main__":
    main()
