"""
TapNQue SMS Notification Service.
Provides asynchronous, non-blocking SMS dispatch via Cloud API (Semaphore/PhilSMS)
with built-in Mock Simulation Mode for capstone defenses and rehearsals.
"""

import json
import logging
import queue
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from tapnque.config import SMS_GATEWAY_URL
from tapnque.core.database import get_database

logger = logging.getLogger("tapnque.sms")

# Global in-memory log of simulated SMS dispatches (for defense demonstration)
MOCK_SMS_HISTORY: List[Dict[str, Any]] = []
_MOCK_HISTORY_LOCK = threading.Lock()


# ==================== Phone Number Validation ====================

def sanitize_ph_phone_number(raw_phone: Optional[str]) -> Optional[str]:
    """
    Sanitize and validate a Philippine mobile phone number.
    Supports formats:
      - 09XXXXXXXXX (11 digits)
      - +639XXXXXXXXX
      - 639XXXXXXXXX
      - 9XXXXXXXXX (10 digits)
      - With dashes, spaces, or parentheses (e.g. 0917-123-4567, (0917) 123 4567)

    Returns:
      Normalized 11-digit string starting with '09' (e.g. '09171234567'),
      or None if invalid.
    """
    if not raw_phone:
        return None

    # Strip non-numeric characters except leading +
    cleaned = re.sub(r"[^\d+]", "", str(raw_phone).strip())
    if not cleaned:
        return None

    # Handle international prefixes
    if cleaned.startswith("+63"):
        cleaned = "0" + cleaned[3:]
    elif cleaned.startswith("63"):
        cleaned = "0" + cleaned[2:]
    elif len(cleaned) == 10 and cleaned.startswith("9"):
        cleaned = "0" + cleaned

    # Must be exactly 11 digits starting with 09
    if len(cleaned) == 11 and cleaned.startswith("09") and cleaned.isdigit():
        return cleaned

    return None


def is_valid_ph_mobile(raw_phone: Optional[str]) -> bool:
    """Check if the provided phone string is a valid Philippine mobile number."""
    return sanitize_ph_phone_number(raw_phone) is not None


# ==================== Template Interpolation ====================

def format_sms_template(template: str, context: Dict[str, Any]) -> str:
    """
    Safely format message templates with context parameters.
    Replaces {ticket}, {name}, {position}, {purpose}, {counter}.
    """
    ticket_raw = context.get("ticket", "")
    if isinstance(ticket_raw, int):
        ticket_str = f"{ticket_raw:04d}"
    else:
        ticket_str = str(ticket_raw)

    safe_dict = {
        "name": str(context.get("name", "Student")).strip(),
        "ticket": ticket_str,
        "position": str(context.get("position", "1")),
        "purpose": str(context.get("purpose", "Assistance")).strip(),
        "counter": str(context.get("counter", "1")),
    }

    result = template
    for key, val in safe_dict.items():
        result = result.replace(f"{{{key}}}", val)
    return result


# ==================== Cloud Gateway & Mock Engine ====================

def send_via_gateway(
    phone: str,
    message: str,
    api_key: str,
    sender_name: str,
    gateway_url: str = SMS_GATEWAY_URL,
    timeout: int = 8,
) -> Tuple[bool, str, Optional[str]]:
    """
    Send SMS via cloud REST API (Semaphore format).
    Returns (success: bool, status: str, detail_or_error: Optional[str]).
    """
    if not api_key:
        return False, "failed", "API key is missing or not configured."

    payload = {
        "apikey": api_key,
        "number": phone,
        "message": message,
    }
    if sender_name:
        payload["sendername"] = sender_name

    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        gateway_url,
        data=data,
        headers={
            "User-Agent": "TapNQue-Kiosk/2.0",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            logger.info("Cloud SMS API response: %s", body)
            return True, "sent", body
    except urllib.error.HTTPError as err:
        err_msg = f"HTTP {err.code}: {err.reason}"
        try:
            body = err.read().decode("utf-8")
            err_msg += f" - {body}"
        except Exception:
            pass
        logger.warning("SMS gateway HTTP error: %s", err_msg)
        return False, "failed", err_msg
    except Exception as exc:
        err_msg = str(exc)
        logger.warning("SMS gateway network error: %s", err_msg)
        return False, "failed", err_msg


def simulate_mock_sms(
    phone: str,
    message: str,
    event_type: str,
    ticket_number: Optional[int] = None,
) -> Tuple[bool, str, Optional[str]]:
    """
    Simulate SMS dispatch locally without consuming gateway credits or requiring internet.
    Records delivery in memory and updates SQLite.
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "ticket_number": ticket_number,
        "phone": phone,
        "event_type": event_type,
        "message": message,
        "status": "mock_sent",
    }
    with _MOCK_HISTORY_LOCK:
        MOCK_SMS_HISTORY.append(entry)
        # Keep maximum of 100 historical records in memory
        if len(MOCK_SMS_HISTORY) > 100:
            MOCK_SMS_HISTORY.pop(0)

    print(
        f"\n📱 [MOCK SMS SIMULATION] To: {phone} | Event: {event_type.upper()} "
        f"| Ticket: #{ticket_number or 0:04d}\n"
        f"   \"{message}\"\n"
    )
    return True, "mock_sent", None


def get_mock_sms_history() -> List[Dict[str, Any]]:
    """Get snapshot of simulated SMS records."""
    with _MOCK_HISTORY_LOCK:
        return list(MOCK_SMS_HISTORY)


def clear_mock_sms_history():
    """Clear simulated SMS records."""
    with _MOCK_HISTORY_LOCK:
        MOCK_SMS_HISTORY.clear()


# ==================== Asynchronous Queue Worker ====================

class _SMSQueueManager:
    """Thread-safe worker managing the background dispatch queue.

    The worker thread starts lazily on the first dispatch so importing this
    module (CLI tools, test runners) never spawns a thread. The queue is
    bounded: under a sustained gateway outage, new dispatches are dropped and
    logged instead of growing memory without limit.
    """

    MAX_PENDING = 500

    def __init__(self):
        self._queue: queue.Queue = queue.Queue(maxsize=self.MAX_PENDING)
        self._worker_thread: Optional[threading.Thread] = None
        self._start_lock = threading.Lock()

    def _ensure_worker(self):
        """Start the daemon worker thread on first use."""
        with self._start_lock:
            if self._worker_thread is None:
                self._worker_thread = threading.Thread(
                    target=self._worker_loop,
                    name="TapNQue-SMSWorker",
                    daemon=True,
                )
                self._worker_thread.start()

    def enqueue(
        self,
        phone: str,
        message: str,
        event_type: str,
        ticket_number: Optional[int] = None,
    ):
        """Enqueue an SMS task for asynchronous non-blocking processing."""
        self._ensure_worker()
        try:
            self._queue.put_nowait((phone, message, event_type, ticket_number))
        except queue.Full:
            logger.error(
                "SMS dispatch queue is full (%d pending); dropping %s SMS for ticket %s",
                self.MAX_PENDING,
                event_type,
                ticket_number,
            )

    def _worker_loop(self):
        while True:
            try:
                phone, message, event_type, ticket_number = self._queue.get()
                self._process_task(phone, message, event_type, ticket_number)
            except Exception as exc:
                logger.error("Error in SMS worker loop: %s", exc)
            finally:
                self._queue.task_done()

    def _process_task(
        self,
        phone: str,
        message: str,
        event_type: str,
        ticket_number: Optional[int],
    ):
        db = get_database()
        settings = db.get_sms_settings()

        if not settings.get("sms_enabled", True):
            logger.info("SMS feature is disabled in settings. Skipping dispatch.")
            if ticket_number:
                db.update_ticket_sms_status(ticket_number, event_type, "disabled", "SMS disabled in settings")
            return

        is_mock = settings.get("sms_mock_mode", True)
        api_key = settings.get("sms_api_key", "").strip()
        sender_name = settings.get("sms_sender_name", "TapNQue").strip()

        # If mock mode is active, or if API key is not configured, fallback to simulation
        if is_mock or not api_key:
            success, status, err = simulate_mock_sms(phone, message, event_type, ticket_number)
        else:
            success, status, err = send_via_gateway(phone, message, api_key, sender_name)

        if ticket_number:
            db.update_ticket_sms_status(ticket_number, event_type, status, err)


# Global singleton queue manager
_queue_manager = _SMSQueueManager()


# ==================== High-Level Public Trigger API ====================

def send_ticket_created_sms(ticket: Dict[str, Any], queue_position: int) -> bool:
    """
    Trigger SMS notification for a newly created ticket.
    Returns True if successfully validated and queued, False otherwise.
    """
    raw_phone = ticket.get("phone") or ticket.get("phone_formatted")
    sanitized = sanitize_ph_phone_number(raw_phone)
    if not sanitized:
        return False

    db = get_database()
    settings = db.get_sms_settings()
    template = settings.get(
        "sms_template_created",
        "Hello {name}! Ticket #{ticket} is confirmed. Line position: {position}. Purpose: {purpose}. - TapNQue",
    )

    context = {
        "name": ticket.get("name", "Student"),
        "ticket": ticket.get("ticket_number", 0),
        "position": queue_position,
        "purpose": ticket.get("purpose", ""),
    }
    message = format_sms_template(template, context)
    _queue_manager.enqueue(sanitized, message, "created", ticket.get("ticket_number"))
    return True


def send_ticket_called_sms(ticket: Dict[str, Any], counter_id: int) -> bool:
    """
    Trigger SMS alert when a ticket is called at a counter.
    Returns True if successfully validated and queued, False otherwise.
    """
    raw_phone = ticket.get("phone") or ticket.get("phone_formatted")
    sanitized = sanitize_ph_phone_number(raw_phone)
    if not sanitized:
        return False

    db = get_database()
    settings = db.get_sms_settings()
    template = settings.get(
        "sms_template_called",
        "ALERT: Ticket #{ticket} ({name}) is NOW BEING CALLED at Counter {counter}. Please proceed immediately within 3 minutes. - TapNQue",
    )

    context = {
        "name": ticket.get("name", "Student"),
        "ticket": ticket.get("ticket_number", 0),
        "counter": counter_id,
        "purpose": ticket.get("purpose", ""),
    }
    message = format_sms_template(template, context)
    _queue_manager.enqueue(sanitized, message, "called", ticket.get("ticket_number"))
    return True


def send_ticket_completed_sms(ticket: Dict[str, Any]) -> bool:
    """
    Trigger SMS notification when a ticket is marked completed.
    Returns True if successfully validated and queued, False otherwise.
    This event is optional: it can be toggled via the sms_completed_enabled
    setting in the Super Admin console.
    """
    raw_phone = ticket.get("phone") or ticket.get("phone_formatted")
    sanitized = sanitize_ph_phone_number(raw_phone)
    if not sanitized:
        return False

    db = get_database()
    settings = db.get_sms_settings()

    if not settings.get("sms_completed_enabled", True):
        logger.info(
            "Completed SMS is disabled in settings. Skipping ticket %s.",
            ticket.get("ticket_number"),
        )
        return False

    template = settings.get(
        "sms_template_completed",
        "Ticket #{ticket} completed. Thank you for visiting TapNQue!",
    )

    context = {
        "name": ticket.get("name", "Student"),
        "ticket": ticket.get("ticket_number", 0),
        "purpose": ticket.get("purpose", ""),
    }
    message = format_sms_template(template, context)
    _queue_manager.enqueue(sanitized, message, "completed", ticket.get("ticket_number"))
    return True
