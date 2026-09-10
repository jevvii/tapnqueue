"""
Email Notification Service for TapNQue.
Provides asynchronous email dispatch via SMTP without blocking the Qt event loop.
"""

import logging
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from tapnque.config import SENDER_EMAIL, SENDER_PASSWORD, SMTP_PORT, SMTP_SERVER

logger = logging.getLogger("tapnque.email")


def is_email_configured() -> bool:
    """Check if SMTP sender credentials are provided via environment variables."""
    return bool(SENDER_EMAIL and SENDER_PASSWORD)


def _send_email_sync(to_email: str, subject: str, body: str) -> bool:
    """Internal synchronous email sender."""
    if not is_email_configured() or not to_email:
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=8)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        logger.info("Email successfully sent to %s: %s", to_email, subject)
        return True
    except Exception as exc:
        logger.warning("Failed to send email to %s: %s", to_email, exc)
        return False


def send_email_async(to_email: str, subject: str, body: str) -> threading.Thread:
    """Send email in a background daemon thread to keep UI responsive."""
    thread = threading.Thread(
        target=_send_email_sync,
        args=(to_email, subject, body),
        name=f"EmailThread-{to_email}",
        daemon=True,
    )
    thread.start()
    return thread


def send_ticket_email(
    to_email: str,
    student_name: str,
    ticket_number: int,
    position: int,
    reason: str,
    async_send: bool = True,
) -> bool:
    """Send ticket confirmation receipt to student email."""
    subject = f"Your Ticket #{ticket_number:04d} - TapNQue"
    body = f"""Hello {student_name},

Your Ticket Number: #{ticket_number:04d}
Position in Line: {position}
Reason: {reason}

Please wait for your number to be called on the waiting area screen.

- TapNQue Student Queue Management
"""
    if async_send:
        send_email_async(to_email, subject, body)
        return True
    return _send_email_sync(to_email, subject, body)


def send_called_email(
    to_email: str,
    student_name: str,
    ticket_number: int,
    reason: str,
    counter_id: Optional[int] = None,
    async_send: bool = True,
) -> bool:
    """Send alert to student when their ticket is called."""
    counter_text = f"Counter {counter_id}" if counter_id else "the counter"
    subject = f"Ticket #{ticket_number:04d} - Please Proceed to {counter_text}"
    body = f"""Hello {student_name},

Your ticket #{ticket_number:04d} for "{reason}" is NOW BEING CALLED.

Please proceed to {counter_text} immediately.
If you do not arrive within a few minutes, your ticket may be skipped.

- TapNQue Student Queue Management
"""
    if async_send:
        send_email_async(to_email, subject, body)
        return True
    return _send_email_sync(to_email, subject, body)


def send_served_email(
    to_email: str,
    student_name: str,
    ticket_number: int,
    reason: str,
    async_send: bool = True,
) -> bool:
    """Send confirmation when student ticket is marked completed."""
    subject = f"Your Ticket #{ticket_number:04d} Has Been Served"
    body = f"""Hello {student_name},

Your ticket #{ticket_number:04d} for "{reason}" has now been marked as completed.

Thank you for visiting!

- TapNQue Student Queue Management
"""
    if async_send:
        send_email_async(to_email, subject, body)
        return True
    return _send_email_sync(to_email, subject, body)
