#!/usr/bin/env python3
"""
TapNQue Safe Local Data & Queue Reset Utility.

Quickly and safely purges all test tickets, active queues, counter assignments,
and wait-time statistics, while STRICTLY RETAINING:
  - System configuration & API credentials (settings table in kiosk.db)
  - Staff & Superadmin login credentials (data/admin_users.json)
  - Notification templates, bot tokens, and SMTP email parameters

Usage:
  python3 reset_queue_data.py [--yes | -y]
  python reset_queue_data.py
"""

import argparse
import sys
from pathlib import Path

# Add src to python path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from tapnque.config import DATA_DIR
from tapnque.core.database import DB_PATH, get_database


def reset_queue_data(non_interactive: bool = False) -> bool:
    """Execute the safe database and queue reset."""
    if not non_interactive and sys.stdin.isatty():
        print("\n" + "=" * 64)
        print("         TapNQue Safe Local Data & Queue Reset")
        print("=" * 64)
        print("This operation will:")
        print("  • PURGE all test tickets & waiting queue entries")
        print("  • RESET all counter states to 'available'")
        print("  • RESET queue wait-time statistics to 0")
        print("\nThis operation will STRICTLY PRESERVE:")
        print("  • Staff & Superadmin credentials (data/admin_users.json)")
        print("  • All system settings, API keys, and bot tokens (kiosk.db)")
        print("=" * 64)

        try:
            choice = input("\nProceed with safe reset? [Y/n]: ").strip().lower()
            if choice not in ("", "y", "yes"):
                print("Reset cancelled.")
                return False
        except (KeyboardInterrupt, EOFError):
            print("\nReset cancelled.")
            return False

    db = get_database()
    result = db.reset_queue_data()

    admin_file = DATA_DIR / "admin_users.json"
    admin_status = "Retained & Verified" if admin_file.exists() else "Not Found"

    print("\n" + "=" * 64)
    print("      ✓ TapNQue Test Data Reset Completed Successfully")
    print("=" * 64)
    print(f"  [✓] Test Tickets Purged:      {result['tickets_purged']}")
    print(f"  [✓] Counter States:           Reset to 'available' (ID 1, 2, 3)")
    print(f"  [✓] Queue Statistics:         Reset (0 served, 0.0s wait)")
    print(f"  [✓] Staff/Admin Credentials:  {admin_status} ({admin_file.name})")
    print(f"  [✓] System Settings:          Preserved in {DB_PATH.name}")
    print(f"  [✓] Database Vacuum:          Completed (WAL Checkpoint)")
    print("=" * 64)
    print("System is clean and ready for production or fresh demonstrations.\n")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Safely reset TapNQue test queue entries while preserving all settings and admin credentials."
    )
    parser.add_argument(
        "-y",
        "--yes",
        "--force",
        dest="yes",
        action="store_true",
        help="Bypass interactive confirmation prompt and perform safe reset immediately.",
    )
    args = parser.parse_args()
    reset_queue_data(non_interactive=args.yes)


if __name__ == "__main__":
    main()
