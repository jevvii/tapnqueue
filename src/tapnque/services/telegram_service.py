"""
TapNQue Telegram Bot & QR Code Notification Service.
Provides asynchronous, non-blocking alert dispatches via official Telegram Bot API
with deep-linking QR code generation and built-in Mock Simulation Mode for capstone defenses.
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
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from tapnque.config import (
    DEFAULT_TELEGRAM_ENABLED,
    DEFAULT_TELEGRAM_MOCK_MODE,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_BOT_USERNAME,
)
from tapnque.core.database import get_database

logger = logging.getLogger("tapnque.telegram")

# Global in-memory log of simulated Telegram dispatches (for defense demonstration)
MOCK_TELEGRAM_HISTORY: List[Dict[str, Any]] = []
_MOCK_TELEGRAM_LOCK = threading.Lock()


# ==================== Link & QR Code Generation ====================

def get_telegram_bot_link(ticket_number: Optional[int] = None) -> str:
    """
    Generate deep-linking Telegram Bot URL.
    Format: https://t.me/<bot_username>?start=ticket_<ticket_number>
    """
    db = get_database()
    settings = db.get_telegram_settings()
    username = settings.get("telegram_bot_username", TELEGRAM_BOT_USERNAME) or "TapNQueBot"
    username = username.strip().lstrip("@")

    if ticket_number:
        return f"https://t.me/{username}?start=ticket_{ticket_number:04d}"
    return f"https://t.me/{username}"


def generate_telegram_qr_pixmap(data_or_ticket: Any, size: int = 180):
    """
    Generate a high-resolution QR code QPixmap encoding the Telegram bot deep-link.
    """
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPixmap
    except ImportError:
        return None

    if QGuiApplication.instance() is None:
        return None

    if isinstance(data_or_ticket, int):
        data = get_telegram_bot_link(data_or_ticket)
    else:
        data = str(data_or_ticket)

    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#102a43", back_color="#ffffff")

        buf = BytesIO()
        img.save(buf, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())
        return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception as exc:
        logger.warning("Failed to generate QR with qrcode library: %s. Using stylized fallback.", exc)

    # Fallback visual matrix representation if qrcode library is absent
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("#ffffff"))
    painter = QPainter(pixmap)
    painter.setPen(QColor("#102a43"))
    painter.drawRect(2, 2, size - 4, size - 4)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, f"TELEGRAM QR\n\n{data[:24]}...")
    painter.end()
    return pixmap


# ==================== Template Interpolation ====================

def format_telegram_template(template: str, context: Dict[str, Any]) -> str:
    """
    Format message templates for Telegram with context parameters.
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


# ==================== Cloud Bot API & Mock Simulator ====================

def send_via_telegram_api(
    chat_id: str,
    text: str,
    bot_token: str,
    parse_mode: str = "Markdown",
    timeout: int = 8,
) -> Tuple[bool, str, Optional[str]]:
    """
    Dispatch message via official Telegram Bot API (sendMessage).
    Endpoint: https://api.telegram.org/bot<token>/sendMessage
    """
    if not bot_token:
        return False, "failed", "Telegram bot token is missing or not configured."

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "TapNQue-TelegramBot/2.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            logger.info("Telegram Bot API response: %s", body)
            return True, "sent", body
    except urllib.error.HTTPError as err:
        err_msg = f"HTTP {err.code}: {err.reason}"
        try:
            body = err.read().decode("utf-8")
            err_msg += f" - {body}"
        except Exception:
            pass
        logger.warning("Telegram Bot HTTP error: %s", err_msg)
        return False, "failed", err_msg
    except Exception as exc:
        err_msg = str(exc)
        logger.warning("Telegram Bot network error: %s", err_msg)
        return False, "failed", err_msg


def simulate_mock_telegram(
    chat_id: str,
    text: str,
    event_type: str,
    ticket_number: Optional[int] = None,
) -> Tuple[bool, str, Optional[str]]:
    """
    Simulate Telegram bot alert locally without requiring internet or an active bot token.
    Records delivery in memory and updates SQLite.
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "ticket_number": ticket_number,
        "chat_id": chat_id,
        "event_type": event_type,
        "message": text,
        "status": "mock_sent",
    }
    with _MOCK_TELEGRAM_LOCK:
        MOCK_TELEGRAM_HISTORY.append(entry)
        if len(MOCK_TELEGRAM_HISTORY) > 100:
            MOCK_TELEGRAM_HISTORY.pop(0)

    print(
        f"\n✈️ [TELEGRAM BOT SIMULATION] To: {chat_id} | Event: {event_type.upper()} "
        f"| Ticket: #{ticket_number or 0:04d}\n"
        f"   \"{text}\"\n"
    )
    return True, "mock_sent", None


def get_mock_telegram_history() -> List[Dict[str, Any]]:
    """Get snapshot of simulated Telegram records."""
    with _MOCK_TELEGRAM_LOCK:
        return list(MOCK_TELEGRAM_HISTORY)


def clear_mock_telegram_history():
    """Clear simulated Telegram records."""
    with _MOCK_TELEGRAM_LOCK:
        MOCK_TELEGRAM_HISTORY.clear()


# ==================== Asynchronous Queue Worker ====================

class _TelegramQueueManager:
    """Thread-safe background queue worker for Telegram dispatches."""

    MAX_PENDING = 500

    def __init__(self):
        self._queue: queue.Queue = queue.Queue(maxsize=self.MAX_PENDING)
        self._worker_thread: Optional[threading.Thread] = None
        self._start_lock = threading.Lock()

    def _ensure_worker(self):
        with self._start_lock:
            if self._worker_thread is None:
                self._worker_thread = threading.Thread(
                    target=self._worker_loop,
                    name="TapNQue-TelegramWorker",
                    daemon=True,
                )
                self._worker_thread.start()

    def enqueue(
        self,
        chat_id: str,
        text: str,
        event_type: str,
        ticket_number: Optional[int] = None,
    ):
        self._ensure_worker()
        try:
            self._queue.put_nowait((chat_id, text, event_type, ticket_number))
        except queue.Full:
            logger.error(
                "Telegram dispatch queue full; dropping %s message for ticket %s",
                event_type,
                ticket_number,
            )

    def _worker_loop(self):
        while True:
            try:
                chat_id, text, event_type, ticket_number = self._queue.get()
                self._process_task(chat_id, text, event_type, ticket_number)
            except Exception as exc:
                logger.error("Error in Telegram worker loop: %s", exc)
            finally:
                self._queue.task_done()

    def _process_task(
        self,
        chat_id: str,
        text: str,
        event_type: str,
        ticket_number: Optional[int],
    ):
        db = get_database()
        settings = db.get_telegram_settings()

        if not settings.get("telegram_enabled", True):
            logger.info("Telegram feature is disabled in settings. Skipping dispatch.")
            if ticket_number:
                db.update_ticket_telegram_status(
                    ticket_number, event_type, "disabled", "Telegram disabled in settings"
                )
            return

        is_mock = settings.get("telegram_mock_mode", True)
        bot_token = settings.get("telegram_bot_token", "").strip()

        if is_mock or not bot_token:
            success, status, err = simulate_mock_telegram(chat_id, text, event_type, ticket_number)
        else:
            success, status, err = send_via_telegram_api(chat_id, text, bot_token)

        if ticket_number:
            db.update_ticket_telegram_status(ticket_number, event_type, status, err)


# Global singleton queue manager
_telegram_queue = _TelegramQueueManager()


# ==================== High-Level Public Trigger API ====================

def send_ticket_created_telegram(ticket: Dict[str, Any], queue_position: int) -> bool:
    """
    Trigger Telegram notification for a newly created ticket.
    """
    chat_id = ticket.get("telegram_chat_id")
    if not chat_id:
        return False

    db = get_database()
    settings = db.get_telegram_settings()
    template = settings.get(
        "telegram_template_created",
        "🎟️ *TapNQue Ticket Confirmation*\n\nHello *{name}*!\nTicket Number: *#{ticket}*\nPosition: *{position}*\nPurpose: *{purpose}*\n\nPlease watch the lobby monitor screen for your number to be called!",
    )

    context = {
        "name": ticket.get("name", "Student"),
        "ticket": ticket.get("ticket_number", 0),
        "position": queue_position,
        "purpose": ticket.get("purpose", ""),
    }
    text = format_telegram_template(template, context)
    _telegram_queue.enqueue(chat_id, text, "created", ticket.get("ticket_number"))
    return True


def send_ticket_called_telegram(ticket: Dict[str, Any], counter_id: int) -> bool:
    """
    Trigger Telegram alert when a ticket is called at a service counter.
    """
    chat_id = ticket.get("telegram_chat_id")
    if not chat_id:
        return False

    db = get_database()
    settings = db.get_telegram_settings()
    template = settings.get(
        "telegram_template_called",
        "🔔 *NOW SERVING ALERT*\n\nTicket *#{ticket}* (*{name}*), please proceed to *Counter {counter}* immediately!\n\n_TapNQue Student Queue Management_",
    )

    context = {
        "name": ticket.get("name", "Student"),
        "ticket": ticket.get("ticket_number", 0),
        "counter": counter_id,
        "purpose": ticket.get("purpose", ""),
    }
    text = format_telegram_template(template, context)
    _telegram_queue.enqueue(chat_id, text, "called", ticket.get("ticket_number"))
    return True


def send_ticket_completed_telegram(ticket: Dict[str, Any]) -> bool:
    """
    Trigger Telegram notification when a ticket is marked completed.
    """
    chat_id = ticket.get("telegram_chat_id")
    if not chat_id:
        return False

    db = get_database()
    settings = db.get_telegram_settings()
    template = settings.get(
        "telegram_template_completed",
        "✅ *Service Completed*\n\nTicket *#{ticket}* has now been marked as completed. Thank you for visiting TapNQue!",
    )

    context = {
        "name": ticket.get("name", "Student"),
        "ticket": ticket.get("ticket_number", 0),
        "purpose": ticket.get("purpose", ""),
    }
    text = format_telegram_template(template, context)
    _telegram_queue.enqueue(chat_id, text, "completed", ticket.get("ticket_number"))
    return True
