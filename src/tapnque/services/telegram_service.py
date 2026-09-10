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
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from tapnque.config import (
    DEFAULT_TELEGRAM_ENABLED,
    DEFAULT_TELEGRAM_MOCK_MODE,
    DEFAULT_TELEGRAM_TEMPLATE_CALLED,
    DEFAULT_TELEGRAM_TEMPLATE_COMPLETED,
    DEFAULT_TELEGRAM_TEMPLATE_CREATED,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_BOT_USERNAME,
)
from tapnque.core.database import get_database

logger = logging.getLogger("tapnque.telegram")

# Global in-memory log of simulated Telegram dispatches (for defense demonstration)
MOCK_TELEGRAM_HISTORY: List[Dict[str, Any]] = []
_MOCK_TELEGRAM_LOCK = threading.Lock()

# Settings-table key storing the rolling roster of recent bot contacts (JSON list)
RECENT_USERS_SETTING_KEY = "telegram_recent_users"


# ==================== Link & QR Code Generation ====================

def get_telegram_bot_link(ticket_number: Optional[int] = None) -> str:
    """
    Generate deep-linking Telegram Bot URL.
    Format: https://t.me/<bot_username>?start=ticket_<ticket_number>
    """
    db = get_database()
    settings = db.get_telegram_settings()
    username = settings.get("telegram_bot_username", TELEGRAM_BOT_USERNAME) or ""
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

def fetch_recent_telegram_users(bot_token: str, timeout: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve users who recently interacted with the bot, for one-tap test dispatch.
    Merges two sources:
      1. Locally recorded contacts captured by the background link listener
         (persists across polling acknowledgment and app restarts).
      2. Pending getUpdates from the Telegram API (unacknowledged updates only).
    Returns a list of dicts with keys: chat_id, username, first_name, last_name, display_name.
    """
    users: List[Dict[str, Any]] = []
    seen_ids = set()

    db = get_database()
    try:
        cached = json.loads(db.get_setting(RECENT_USERS_SETTING_KEY, "[]") or "[]")
        if isinstance(cached, list):
            for entry in cached:
                chat_id = str(entry.get("chat_id", ""))
                if chat_id and chat_id not in seen_ids:
                    seen_ids.add(chat_id)
                    users.append(
                        {
                            "chat_id": chat_id,
                            "username": (entry.get("username") or "").strip().lstrip("@"),
                            "first_name": (entry.get("first_name") or "").strip(),
                            "last_name": (entry.get("last_name") or "").strip(),
                            "display_name": entry.get("display_name") or f"User {chat_id}",
                        }
                    )
    except (ValueError, TypeError):
        pass

    if not bot_token:
        return users

    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "TapNQue-TelegramBot/2.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not data.get("ok"):
                return users
            for item in reversed(data.get("result", [])):
                msg = (
                    item.get("message")
                    or item.get("edited_message")
                    or item.get("callback_query", {}).get("message")
                )
                if not msg:
                    continue
                chat = msg.get("chat") or {}
                chat_id = chat.get("id")
                if chat_id and str(chat_id) not in seen_ids:
                    seen_ids.add(str(chat_id))
                    username = (chat.get("username") or "").strip().lstrip("@")
                    first_name = (chat.get("first_name") or "").strip()
                    last_name = (chat.get("last_name") or "").strip()
                    display_parts = [p for p in (first_name, last_name) if p]
                    display_name = " ".join(display_parts) if display_parts else (username or f"User {chat_id}")
                    users.append({
                        "chat_id": str(chat_id),
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                        "display_name": display_name,
                    })
            return users
    except Exception as exc:
        logger.debug("Failed to fetch Telegram getUpdates: %s", exc)
        return users


def resolve_telegram_chat_id(target: str, bot_token: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve a target string to a valid Telegram numeric chat ID.
    If target is numeric (or starts with - for groups/channels), returns it directly.
    If target is an @username, scans recent bot updates to match it to a numeric chat ID.
    Returns (resolved_chat_id, error_message).
    """
    cleaned = (target or "").strip()
    if not cleaned:
        return None, "Chat ID or Username cannot be empty."

    # Direct numeric Chat ID (user ID e.g. 123456789 or group ID e.g. -100123456789)
    if cleaned.lstrip("-").isdigit():
        return cleaned, None

    # Check if someone accidentally passed a Philippine phone number
    digits_only = re.sub(r"[^\d]", "", cleaned)
    if (len(digits_only) == 11 and digits_only.startswith("09")) or (len(digits_only) == 12 and digits_only.startswith("639")):
        return None, (
            "Telegram Bot API does not support phone numbers as chat recipients.\n"
            "Please use your numeric Telegram Chat ID (check @userinfobot)\n"
            "or your @username after sending /start to your bot."
        )

    # Username resolution (@username or username)
    clean_username = cleaned.lstrip("@").lower()
    if bot_token:
        recent_users = fetch_recent_telegram_users(bot_token)
        for u in recent_users:
            if u["username"].lower() == clean_username:
                logger.info("Resolved @%s to Telegram Chat ID %s", clean_username, u["chat_id"])
                return u["chat_id"], None

    return None, (
        f"Could not find an active Telegram chat for '@{clean_username}'.\n\n"
        f"In Telegram:\n"
        f"1. Open your TapNQue bot on the phone or PC.\n"
        f"2. Tap 'START' (or send /start) so the bot has permission to message you.\n"
        f"3. Enter your numeric Chat ID (check @userinfobot) or try again with @{clean_username}."
    )


def validate_telegram_bot_token(bot_token: str, timeout: int = 6) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate a bot token against the official getMe endpoint.
    Returns (is_valid, bot_username, error_message). On success the username can be
    used to auto-configure the deep-link QR code so admins never type it by hand.
    """
    token = (bot_token or "").strip()
    if not token:
        return False, None, "Bot token is empty."

    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "TapNQue-TelegramBot/2.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok") and isinstance(data.get("result"), dict):
                username = (data["result"].get("username") or "").strip().lstrip("@")
                return True, username or None, None
            return False, None, "Unexpected response from Telegram getMe."
    except urllib.error.HTTPError as err:
        if err.code in (401, 404):
            return False, None, "Invalid bot token. Copy the exact token from @BotFather and try again."
        return False, None, f"Telegram rejected the token (HTTP {err.code})."
    except Exception as exc:
        return False, None, f"Could not reach api.telegram.org: {exc}"


def parse_start_payload(payload: str) -> Optional[int]:
    """
    Extract a ticket number from a /start deep-link payload.
    Accepts 'ticket_0042', 'ticket-42', '42', etc. Returns None when no ticket matches.
    """
    text = (payload or "").strip()
    if not text:
        return None
    match = re.search(r"ticket[_-]?(\d{1,7})", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    if text.isdigit():
        return int(text)
    return None


def is_telegram_qr_available() -> bool:
    """
    True when the kiosk ticket dialog should offer the scan-to-link QR card:
    the Telegram feature is enabled and a real bot username is configured.
    """
    db = get_database()
    settings = db.get_telegram_settings()
    if not settings.get("telegram_enabled", True):
        return False
    username = (settings.get("telegram_bot_username", "") or "").strip().lstrip("@")
    return bool(username)


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

    # Auto-resolve username or validate numeric chat_id
    resolved_id, resolve_err = resolve_telegram_chat_id(chat_id, bot_token)
    if not resolved_id:
        return False, "failed", resolve_err or "Invalid Telegram chat ID."

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": resolved_id,
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
        if "chat not found" in err_msg.lower():
            err_msg += (
                "\n\nHint: Telegram bots cannot initiate chats with users first. "
                "Open your bot in Telegram (@OlfuTapNQue_bot), tap 'START', and try again."
            )
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
        ensure_link_listener()

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


# ==================== Deep-Link Auto-Link Listener ====================

class _TelegramLinkListener:
    """
    Background getUpdates long-poll listener that makes the QR deep-link flow
    fully automatic. When a student scans the ticket QR and taps START in
    Telegram, the bot receives '/start ticket_XXXX'; this listener binds that
    user's chat ID to the ticket and dispatches the confirmation alert — no
    chat-ID typing, no manual setup, works even for first-time Telegram users.
    """

    POLL_INTERVAL_SECONDS = 2
    LONG_POLL_TIMEOUT = 25
    OFFSET_SETTING_KEY = "telegram_update_offset"

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._start_lock = threading.Lock()

    def ensure_started(self):
        with self._start_lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(
                    target=self._run_loop,
                    name="TapNQue-TelegramLinkListener",
                    daemon=True,
                )
                self._thread.start()

    def _run_loop(self):
        while True:
            try:
                db = get_database()
                settings = db.get_telegram_settings()
                token = (settings.get("telegram_bot_token", "") or "").strip()
                listening = (
                    settings.get("telegram_enabled", True)
                    and not settings.get("telegram_mock_mode", True)
                    and bool(token)
                )
                if not listening:
                    time.sleep(5)
                    continue

                offset_raw = db.get_setting(self.OFFSET_SETTING_KEY, "0")
                try:
                    offset = int(offset_raw or 0)
                except (TypeError, ValueError):
                    offset = 0

                updates = self._poll_updates(token, offset)

                max_update_id = offset - 1
                for update in updates:
                    max_update_id = max(max_update_id, update.get("update_id", 0))
                    try:
                        self._handle_update(update)
                    except Exception as exc:
                        logger.warning("Telegram link listener failed to handle update: %s", exc)

                if updates:
                    # Acknowledge processed updates so Telegram never resends them.
                    db.set_setting(self.OFFSET_SETTING_KEY, str(max_update_id + 1))

                if not updates:
                    # _poll_updates long-polls; reaching here means a clean timeout cycle.
                    continue
                time.sleep(self.POLL_INTERVAL_SECONDS)
            except urllib.error.HTTPError as err:
                if err.code == 409:
                    logger.warning(
                        "Telegram getUpdates conflict (a webhook or another poller is active). Backing off."
                    )
                    time.sleep(30)
                else:
                    logger.warning("Telegram link listener HTTP error: %s", err)
                    time.sleep(10)
            except Exception as exc:
                logger.debug("Telegram link listener cycle failed: %s", exc)
                time.sleep(10)

    def _poll_updates(self, token: str, offset: int) -> List[Dict[str, Any]]:
        params = urllib.parse.urlencode(
            {
                "offset": offset,
                "timeout": self.LONG_POLL_TIMEOUT,
                "allowed_updates": json.dumps(["message"]),
            }
        )
        url = f"https://api.telegram.org/bot{token}/getUpdates?{params}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "TapNQue-TelegramBot/2.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=self.LONG_POLL_TIMEOUT + 10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not data.get("ok"):
                return []
            return list(data.get("result", []))

    def _record_recent_user(self, chat: Dict[str, Any]):
        """Keep a rolling roster (max 10) of bot contacts for one-tap test dispatch."""
        chat_id = chat.get("id")
        if not chat_id:
            return
        username = (chat.get("username") or "").strip().lstrip("@")
        first_name = (chat.get("first_name") or "").strip()
        last_name = (chat.get("last_name") or "").strip()
        display_parts = [p for p in (first_name, last_name) if p]
        entry = {
            "chat_id": str(chat_id),
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "display_name": " ".join(display_parts) if display_parts else (username or f"User {chat_id}"),
        }
        try:
            db = get_database()
            roster = json.loads(db.get_setting(RECENT_USERS_SETTING_KEY, "[]") or "[]")
            if not isinstance(roster, list):
                roster = []
            roster = [r for r in roster if str(r.get("chat_id")) != entry["chat_id"]]
            roster.insert(0, entry)
            db.set_setting(RECENT_USERS_SETTING_KEY, json.dumps(roster[:10]))
        except Exception as exc:
            logger.debug("Failed to record recent Telegram user: %s", exc)

    def _handle_update(self, update: Dict[str, Any]):
        message = update.get("message") or {}
        text = (message.get("text") or "").strip()
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if not chat_id:
            return
        self._record_recent_user(chat)
        if not text:
            return

        command, _, payload = text.partition(" ")
        command = command.split("@")[0].lower()  # tolerate '/start@BotName'
        if command != "/start":
            return

        chat_id = str(chat_id)
        db = get_database()
        settings = db.get_telegram_settings()
        token = (settings.get("telegram_bot_token", "") or "").strip()

        ticket_number = parse_start_payload(payload)
        if ticket_number is None:
            # Bare /start with no QR payload: guide brand-new Telegram users.
            welcome = (
                "👋 *Welcome to TapNQue Queue Alerts!*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "TapNQue delivers real-time campus queue alerts straight to your Telegram chat.\n\n"
                "📲 *How to link your ticket:*\n"
                "1️⃣ Take a queue ticket at any TapNQue Kiosk.\n"
                "2️⃣ Scan the *Telegram QR Code* on screen or on your printed slip.\n"
                "3️⃣ Tap *START* in Telegram — your ticket connects instantly!\n\n"
                "_TapNQue • OLFU Student Services_"
            )
            send_via_telegram_api(chat_id, welcome, token)
            logger.info("Sent TapNQue welcome guide to chat %s", chat_id)
            return

        ticket = db.get_ticket(ticket_number)
        if not ticket:
            send_via_telegram_api(
                chat_id,
                f"⚠️ *Ticket Not Found or Expired*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Ticket *#{ticket_number:04d}* could not be found or has already been concluded.\n\n"
                f"ℹ️ *Need assistance?*\n"
                f"Please register for a new ticket at the TapNQue kiosk and scan the on-screen QR code.\n\n"
                f"_TapNQue • OLFU Student Services_",
                token,
            )
            return

        existing_status = db.get_ticket_telegram_status(ticket_number)
        already_linked = (
            ticket.get("telegram_chat_id")
            and existing_status.get("telegram_ticket_status") in ("sent", "mock_sent")
        )
        db.bind_telegram_chat_id(ticket_number, chat_id)
        logger.info(
            "Linked Telegram chat %s to ticket #%04d via QR deep-link",
            chat_id,
            ticket_number,
        )

        if already_linked:
            return  # idempotent: never double-send the confirmation

        linked_ticket = dict(ticket)
        linked_ticket["telegram_chat_id"] = chat_id

        queue_position = 1
        for index, queued_ticket in enumerate(db.get_waiting_queue(), start=1):
            if queued_ticket.get("ticket_number") == ticket_number:
                queue_position = index
                break

        sent = send_ticket_created_telegram(linked_ticket, queue_position)
        if sent:
            logger.info(
                "Auto-dispatched ticket-created Telegram alert for #%04d to chat %s",
                ticket_number,
                chat_id,
            )


_link_listener = _TelegramLinkListener()


def ensure_link_listener():
    """Start (idempotently) the background QR deep-link auto-link listener."""
    _link_listener.ensure_started()


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
    template = settings.get("telegram_template_created", DEFAULT_TELEGRAM_TEMPLATE_CREATED)

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
    template = settings.get("telegram_template_called", DEFAULT_TELEGRAM_TEMPLATE_CALLED)

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
    template = settings.get("telegram_template_completed", DEFAULT_TELEGRAM_TEMPLATE_COMPLETED)

    context = {
        "name": ticket.get("name", "Student"),
        "ticket": ticket.get("ticket_number", 0),
        "purpose": ticket.get("purpose", ""),
    }
    text = format_telegram_template(template, context)
    _telegram_queue.enqueue(chat_id, text, "completed", ticket.get("ticket_number"))
    return True
