"""
TapNQue Services Module
External communication and notification handlers.
"""

from .email_service import (
    is_email_configured,
    send_called_email,
    send_email_async,
    send_served_email,
    send_ticket_email,
)
from .sms_service import (
    clear_mock_sms_history,
    format_sms_template,
    get_mock_sms_history,
    is_valid_ph_mobile,
    sanitize_ph_phone_number,
    send_ticket_called_sms,
    send_ticket_completed_sms,
    send_ticket_created_sms,
)

__all__ = [
    "is_email_configured",
    "send_ticket_email",
    "send_called_email",
    "send_served_email",
    "send_email_async",
    "sanitize_ph_phone_number",
    "is_valid_ph_mobile",
    "format_sms_template",
    "send_ticket_created_sms",
    "send_ticket_called_sms",
    "send_ticket_completed_sms",
    "get_mock_sms_history",
    "clear_mock_sms_history",
]
