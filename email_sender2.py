"""
Legacy shim for email_sender2.py.
Delegates to tapnque.services.email_service.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tapnque.services.email_service import (
    is_email_configured,
    send_called_email,
    send_served_email,
    send_ticket_email,
)

__all__ = [
    "is_email_configured",
    "send_ticket_email",
    "send_called_email",
    "send_served_email",
]
