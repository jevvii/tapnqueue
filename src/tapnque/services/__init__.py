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
from .telegram_service import (
    clear_mock_telegram_history,
    format_telegram_template,
    generate_telegram_qr_pixmap,
    get_mock_telegram_history,
    get_telegram_bot_link,
    send_ticket_called_telegram,
    send_ticket_completed_telegram,
    send_ticket_created_telegram,
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
    "get_telegram_bot_link",
    "generate_telegram_qr_pixmap",
    "format_telegram_template",
    "send_ticket_created_telegram",
    "send_ticket_called_telegram",
    "send_ticket_completed_telegram",
    "get_mock_telegram_history",
    "clear_mock_telegram_history",
]
