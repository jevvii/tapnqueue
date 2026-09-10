"""
Database Manager for TapNQue Student Kiosk Ticketing System.
Robust SQLite-backed local database interface with WAL mode and concurrent access resilience.
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from tapnque.config import (
    DB_PATH,
    DEFAULT_SMS_API_KEY,
    DEFAULT_SMS_ENABLED,
    DEFAULT_SMS_MOCK_MODE,
    DEFAULT_SMS_SENDER_NAME,
    LEGACY_JSON_PATH,
    SMS_GATEWAY_URL,
)

logger = logging.getLogger("tapnque.database")


class DatabaseManager:
    """Central database interface backed by local SQLite database."""

    def __init__(self, db_file: Optional[Path | str] = None):
        self.db_file = Path(db_file).resolve() if db_file else DB_PATH
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()

    @contextmanager
    def _connect(self):
        """Create a configured SQLite connection context that commits and closes cleanly."""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _row_to_dict(self, row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        return {key: row[key] for key in row.keys()}

    def _initialize_db(self):
        """Initialize the SQLite database schema and default records if needed."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_number INTEGER PRIMARY KEY,
                    name TEXT,
                    student_id TEXT,
                    email TEXT,
                    phone TEXT,
                    phone_formatted TEXT,
                    visitor_type TEXT,
                    purpose TEXT,
                    priority_type TEXT DEFAULT 'Standard',
                    created_at TEXT,
                    called_at TEXT,
                    recalled_at TEXT,
                    completed_at TEXT,
                    status TEXT DEFAULT 'waiting',
                    counter_id INTEGER,
                    wait_time REAL,
                    prioritized_at TEXT,
                    sms_ticket_status TEXT DEFAULT 'pending',
                    sms_called_status TEXT DEFAULT 'pending',
                    sms_completed_status TEXT DEFAULT 'pending',
                    sms_last_error TEXT
                )
                """
            )

            # Safely upgrade existing tables if missing new columns
            existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(tickets)").fetchall()}
            upgrade_columns = [
                ("phone_formatted", "TEXT"),
                ("sms_ticket_status", "TEXT DEFAULT 'pending'"),
                ("sms_called_status", "TEXT DEFAULT 'pending'"),
                ("sms_completed_status", "TEXT DEFAULT 'pending'"),
                ("sms_last_error", "TEXT"),
            ]
            for col_name, col_def in upgrade_columns:
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE tickets ADD COLUMN {col_name} {col_def}")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS counters (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    status TEXT,
                    current_ticket INTEGER
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS statistics (
                    key TEXT PRIMARY KEY,
                    value REAL NOT NULL
                )
                """
            )

            default_counters = [
                (1, "Counter 1", "available", None),
                (2, "Counter 2", "available", None),
                (3, "Counter 3", "available", None),
            ]
            existing = conn.execute("SELECT id FROM counters").fetchall()
            existing_ids = {row[0] for row in existing}
            for counter in default_counters:
                if counter[0] not in existing_ids:
                    conn.execute(
                        "INSERT INTO counters (id, name, status, current_ticket) VALUES (?, ?, ?, ?)",
                        counter,
                    )

            default_settings = [
                ("phone_number_enabled", "1"),
                ("sms_enabled", "1" if DEFAULT_SMS_ENABLED else "0"),
                ("sms_mock_mode", "1" if DEFAULT_SMS_MOCK_MODE else "0"),
                ("sms_completed_enabled", "1"),
                ("sms_api_key", DEFAULT_SMS_API_KEY),
                ("sms_sender_name", DEFAULT_SMS_SENDER_NAME),
                ("sms_gateway_url", SMS_GATEWAY_URL),
                (
                    "sms_template_created",
                    "Hello {name}! Ticket #{ticket} is confirmed. Line position: {position}. Purpose: {purpose}. - TapNQue",
                ),
                (
                    "sms_template_called",
                    "ALERT: Ticket #{ticket} ({name}) is NOW BEING CALLED at Counter {counter}. Please proceed immediately within 3 minutes. - TapNQue",
                ),
                (
                    "sms_template_completed",
                    "Ticket #{ticket} completed. Thank you for visiting TapNQue!",
                ),
            ]
            for key, val in default_settings:
                conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, val),
                )

            if conn.execute("SELECT COUNT(*) FROM statistics").fetchone()[0] == 0:
                conn.executemany(
                    "INSERT INTO statistics (key, value) VALUES (?, ?)",
                    [
                        ("total_served", 0.0),
                        ("total_wait_time", 0.0),
                        ("average_wait_time", 0.0),
                    ],
                )

        self._migrate_legacy_json_if_needed()

    def _migrate_legacy_json_if_needed(self):
        """Import existing queue_db.json data into SQLite once, if present and DB is empty."""
        legacy_path = self.db_file.parent / "queue_db.json"
        if not legacy_path.exists() and self.db_file == DB_PATH:
            legacy_path = LEGACY_JSON_PATH
        if not legacy_path.exists():
            return

        with self._connect() as conn:
            if conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] > 0:
                return

            try:
                with open(legacy_path, "r", encoding="utf-8") as f:
                    legacy = json.load(f)
            except (OSError, ValueError, TypeError):
                return

            waiting_queue = legacy.get("waiting_queue", [])
            served_tickets = legacy.get("served_tickets", [])
            counters = legacy.get("counters", [])
            settings = legacy.get("settings", {})
            stats = legacy.get("statistics", {})

            for ticket in waiting_queue + served_tickets:
                conn.execute(
                    """
                    INSERT INTO tickets (
                        ticket_number, name, student_id, email, phone, visitor_type,
                        purpose, priority_type, created_at, called_at, recalled_at,
                        completed_at, status, counter_id, wait_time, prioritized_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ticket.get("ticket_number"),
                        ticket.get("name"),
                        ticket.get("student_id"),
                        ticket.get("email"),
                        ticket.get("phone"),
                        ticket.get("visitor_type"),
                        ticket.get("purpose"),
                        ticket.get("priority_type", "Standard"),
                        ticket.get("created_at"),
                        ticket.get("called_at"),
                        ticket.get("recalled_at"),
                        ticket.get("completed_at"),
                        ticket.get("status", "waiting"),
                        ticket.get("counter_id"),
                        ticket.get("wait_time"),
                        ticket.get("prioritized_at"),
                    ),
                )

            for counter in counters:
                conn.execute(
                    "INSERT OR REPLACE INTO counters (id, name, status, current_ticket) VALUES (?, ?, ?, ?)",
                    (counter.get("id"), counter.get("name"), counter.get("status"), counter.get("current_ticket")),
                )

            if settings:
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    ("phone_number_enabled", "1" if settings.get("phone_number_enabled", True) else "0"),
                )

            if stats:
                conn.executemany(
                    "INSERT OR REPLACE INTO statistics (key, value) VALUES (?, ?)",
                    [
                        ("total_served", float(stats.get("total_served", 0))),
                        ("total_wait_time", float(stats.get("total_wait_time", 0))),
                        ("average_wait_time", float(stats.get("average_wait_time", 0))),
                    ],
                )

    def _save_local_data(self, data: Dict[str, Any]):
        """Legacy compatibility helper for JSON output."""
        try:
            with open(LEGACY_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass

    def _load_data(self) -> Dict:
        """Load data in legacy dictionary shape."""
        return {
            "current_ticket": self.get_next_ticket_number() - 1,
            "waiting_queue": self.get_waiting_queue(),
            "served_tickets": self.get_served_tickets(),
            "counters": self.get_counters(),
            "statistics": self.get_statistics(),
            "settings": self.get_app_settings(),
        }

    def _save_data(self, data: Dict):
        """Compatibility save helper."""
        self._save_local_data(data)

    # ==================== Ticket Operations ====================

    def get_next_ticket_number(self) -> int:
        """Get the next sequential ticket number."""
        with self._connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(ticket_number), 0) + 1 AS next_number FROM tickets").fetchone()
            return int(row["next_number"]) if row else 1

    def create_ticket(
        self,
        name: str,
        student_id: str,
        email: str,
        phone: str,
        purpose: str,
        visitor_type: str = "Student",
        phone_formatted: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new ticket and add to waiting queue."""
        ticket_number = self.get_next_ticket_number()
        timestamp = datetime.now().isoformat()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tickets (
                    ticket_number, name, student_id, email, phone, phone_formatted,
                    visitor_type, purpose, priority_type, created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket_number,
                    name,
                    student_id,
                    email,
                    phone,
                    phone_formatted or phone,
                    visitor_type,
                    purpose,
                    "Standard",
                    timestamp,
                    "waiting",
                ),
            )

        return {
            "ticket_number": ticket_number,
            "name": name,
            "student_id": student_id,
            "email": email,
            "phone": phone,
            "phone_formatted": phone_formatted or phone,
            "visitor_type": visitor_type,
            "purpose": purpose,
            "priority_type": "Standard",
            "created_at": timestamp,
            "status": "waiting",
        }

    def get_ticket(self, ticket_number: int) -> Optional[Dict[str, Any]]:
        """Retrieve a single ticket by number."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tickets WHERE ticket_number = ?", (ticket_number,)).fetchone()
            return self._row_to_dict(row)

    def get_waiting_queue(self) -> List[Dict[str, Any]]:
        """Get all waiting tickets sorted by priority and ticket number."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM tickets
                WHERE status = 'waiting'
                ORDER BY CASE priority_type
                    WHEN 'Urgent' THEN 0
                    WHEN 'High' THEN 1
                    ELSE 2
                END, ticket_number ASC
                """
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_served_tickets(self) -> List[Dict[str, Any]]:
        """Get all active and completed tickets for history."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM tickets
                WHERE status IN ('serving', 'recalled', 'completed')
                ORDER BY ticket_number DESC
                """
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    # ==================== Counter Operations ====================

    def get_counters(self) -> List[Dict[str, Any]]:
        """Get all counter stations."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM counters ORDER BY id ASC").fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_counter(self, counter_id: int) -> Optional[Dict[str, Any]]:
        """Get counter station details by ID."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM counters WHERE id = ?", (counter_id,)).fetchone()
            return self._row_to_dict(row)

    def update_counter_status(self, counter_id: int, status: str):
        """Update counter status."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE counters SET status = ? WHERE id = ?",
                (status, counter_id),
            )

    # ==================== Queue Management ====================

    def call_next_ticket(self, counter_id: int) -> Optional[Dict[str, Any]]:
        """Call the next waiting ticket in queue for the specified counter."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM tickets
                WHERE status = 'waiting'
                ORDER BY CASE priority_type
                    WHEN 'Urgent' THEN 0
                    WHEN 'High' THEN 1
                    ELSE 2
                END, ticket_number ASC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None

            now = datetime.now().isoformat()
            ticket_number = row["ticket_number"]
            conn.execute(
                "UPDATE tickets SET status = 'serving', called_at = ?, counter_id = ? WHERE ticket_number = ?",
                (now, counter_id, ticket_number),
            )
            conn.execute(
                "UPDATE counters SET status = 'busy', current_ticket = ? WHERE id = ?",
                (ticket_number, counter_id),
            )
            updated_row = conn.execute("SELECT * FROM tickets WHERE ticket_number = ?", (ticket_number,)).fetchone()
            return self._row_to_dict(updated_row)

    def prioritize_waiting_ticket(self, ticket_number: int, priority_type: str) -> Optional[Dict[str, Any]]:
        """Set priority level for a waiting ticket."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tickets WHERE ticket_number = ? AND status = 'waiting'",
                (ticket_number,),
            ).fetchone()
            if row is None:
                return None

            now = datetime.now().isoformat()
            conn.execute(
                "UPDATE tickets SET priority_type = ?, prioritized_at = ? WHERE ticket_number = ?",
                (priority_type, now, ticket_number),
            )
            updated_row = conn.execute("SELECT * FROM tickets WHERE ticket_number = ?", (ticket_number,)).fetchone()
            return self._row_to_dict(updated_row)

    def clear_ticket_priority(self, ticket_number: int) -> Optional[Dict[str, Any]]:
        """Reset ticket priority to Standard."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tickets WHERE ticket_number = ? AND status = 'waiting'",
                (ticket_number,),
            ).fetchone()
            if row is None:
                return None

            conn.execute(
                "UPDATE tickets SET priority_type = 'Standard', prioritized_at = NULL WHERE ticket_number = ?",
                (ticket_number,),
            )
            updated_row = conn.execute("SELECT * FROM tickets WHERE ticket_number = ?", (ticket_number,)).fetchone()
            return self._row_to_dict(updated_row)

    def recall_ticket(self, ticket_number: int) -> Optional[Dict[str, Any]]:
        """Recall a ticket currently in service or recalled."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tickets WHERE ticket_number = ? AND status IN ('serving', 'recalled')",
                (ticket_number,),
            ).fetchone()
            if row is None:
                return None

            now = datetime.now().isoformat()
            conn.execute(
                "UPDATE tickets SET status = 'recalled', recalled_at = ? WHERE ticket_number = ?",
                (now, ticket_number),
            )
            updated_row = conn.execute("SELECT * FROM tickets WHERE ticket_number = ?", (ticket_number,)).fetchone()
            return self._row_to_dict(updated_row)

    def mark_ticket_done(self, ticket_number: int) -> Dict[str, Any]:
        """Mark a ticket as completed and record service analytics."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tickets WHERE ticket_number = ?", (ticket_number,)).fetchone()
            if row is None:
                return {"status": "not_found", "ticket_number": ticket_number}

            completed_at = datetime.now().isoformat()
            wait_time = 0.0
            if row["called_at"]:
                created_at = datetime.fromisoformat(row["created_at"])
                called_at = datetime.fromisoformat(row["called_at"])
                wait_time = max(0.0, (called_at - created_at).total_seconds())
            if row["completed_at"] is not None and row["wait_time"] is not None:
                wait_time = float(row["wait_time"])

            conn.execute(
                "UPDATE tickets SET status = 'completed', completed_at = ?, wait_time = ? WHERE ticket_number = ?",
                (completed_at, wait_time, ticket_number),
            )

            conn.execute(
                "UPDATE counters SET status = 'available', current_ticket = NULL WHERE current_ticket = ?",
                (ticket_number,),
            )

            stats_rows = conn.execute("SELECT key, value FROM statistics").fetchall()
            stats = {r["key"]: float(r["value"]) for r in stats_rows}
            stats["total_served"] = int(stats.get("total_served", 0)) + 1
            stats["total_wait_time"] = float(stats.get("total_wait_time", 0)) + float(wait_time)
            stats["average_wait_time"] = (
                stats["total_wait_time"] / stats["total_served"] if stats["total_served"] > 0 else 0.0
            )

            conn.executemany(
                "INSERT INTO statistics (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                [
                    ("total_served", float(stats["total_served"])),
                    ("total_wait_time", float(stats["total_wait_time"])),
                    ("average_wait_time", float(stats["average_wait_time"])),
                ],
            )

        return {"status": "completed", "ticket_number": ticket_number}

    def get_currently_serving(self) -> List[Dict[str, Any]]:
        """Get tickets currently being served or recalled."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tickets WHERE status IN ('serving', 'recalled') ORDER BY ticket_number ASC"
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def clear_completed_tickets(self) -> int:
        """
        Delete completed tickets from the database.
        Returns the number of deleted records.
        """
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM tickets WHERE status = 'completed'")
            return cursor.rowcount

    def delete_ticket(self, ticket_number: int) -> bool:
        """Delete a single ticket by number."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM tickets WHERE ticket_number = ?", (ticket_number,))
            return cursor.rowcount > 0

    # ==================== Statistics ====================

    def _save_statistics(self, stats: Dict[str, Any]):
        """Persist statistics into the database."""
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO statistics (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                [
                    ("total_served", float(stats.get("total_served", 0))),
                    ("total_wait_time", float(stats.get("total_wait_time", 0))),
                    ("average_wait_time", float(stats.get("average_wait_time", 0))),
                ],
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics."""
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM statistics").fetchall()
            values = {row["key"]: float(row["value"]) for row in rows}
            return {
                "total_served": int(values.get("total_served", 0)),
                "total_wait_time": float(values.get("total_wait_time", 0)),
                "average_wait_time": float(values.get("average_wait_time", 0)),
            }

    def reset_statistics(self):
        """Reset all statistics metrics."""
        self._save_statistics({
            "total_served": 0,
            "total_wait_time": 0,
            "average_wait_time": 0,
        })

    # ==================== App Settings ====================

    def get_app_settings(self) -> Dict[str, Any]:
        """Get application settings."""
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = 'phone_number_enabled'").fetchone()
            enabled = bool(int(row["value"])) if row else True
            return {"phone_number_enabled": enabled}

    def get_cached_app_settings(self) -> Dict[str, Any]:
        """Cached/fast settings retrieval."""
        return self.get_app_settings()

    def set_phone_number_enabled(self, enabled: bool):
        """Toggle kiosk phone number field visibility."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('phone_number_enabled', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                ("1" if bool(enabled) else "0",),
            )

    # ==================== SMS Settings & Tracking ====================

    def get_sms_settings(self) -> Dict[str, Any]:
        """Get all SMS gateway and simulation settings."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value FROM settings WHERE key LIKE 'sms_%'"
            ).fetchall()
            kv = {row["key"]: row["value"] for row in rows}

            return {
                "sms_enabled": bool(int(kv.get("sms_enabled", "1" if DEFAULT_SMS_ENABLED else "0"))),
                "sms_mock_mode": bool(int(kv.get("sms_mock_mode", "1" if DEFAULT_SMS_MOCK_MODE else "0"))),
                "sms_completed_enabled": bool(int(kv.get("sms_completed_enabled", "1"))),
                "sms_api_key": kv.get("sms_api_key", DEFAULT_SMS_API_KEY),
                "sms_sender_name": kv.get("sms_sender_name", DEFAULT_SMS_SENDER_NAME),
                "sms_gateway_url": kv.get("sms_gateway_url", SMS_GATEWAY_URL),
                "sms_template_created": kv.get(
                    "sms_template_created",
                    "Hello {name}! Ticket #{ticket} is confirmed. Line position: {position}. Purpose: {purpose}. - TapNQue",
                ),
                "sms_template_called": kv.get(
                    "sms_template_called",
                    "ALERT: Ticket #{ticket} ({name}) is NOW BEING CALLED at Counter {counter}. Please proceed immediately within 3 minutes. - TapNQue",
                ),
                "sms_template_completed": kv.get(
                    "sms_template_completed",
                    "Ticket #{ticket} completed. Thank you for visiting TapNQue!",
                ),
            }

    def update_sms_settings(self, settings_dict: Dict[str, Any]):
        """Persist updated SMS settings into settings table."""
        with self._connect() as conn:
            items = []
            for key, val in settings_dict.items():
                if isinstance(val, bool):
                    db_val = "1" if val else "0"
                else:
                    db_val = str(val or "").strip()
                items.append((key, db_val))

            conn.executemany(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                items,
            )

    def set_sms_enabled(self, enabled: bool):
        """Toggle master SMS feature."""
        self.update_sms_settings({"sms_enabled": bool(enabled)})

    def set_sms_mock_mode(self, enabled: bool):
        """Toggle Mock / Simulation mode."""
        self.update_sms_settings({"sms_mock_mode": bool(enabled)})

    def set_sms_completed_enabled(self, enabled: bool):
        """Toggle the optional Ticket Completed / Served confirmation SMS."""
        self.update_sms_settings({"sms_completed_enabled": bool(enabled)})

    def set_sms_api_key(self, api_key: str):
        """Update cloud SMS gateway API key."""
        self.update_sms_settings({"sms_api_key": api_key.strip()})

    def set_sms_sender_name(self, sender_name: str):
        """Update cloud SMS sender name."""
        self.update_sms_settings({"sms_sender_name": sender_name.strip()})

    def update_ticket_sms_status(
        self,
        ticket_number: int,
        event_type: str,
        status: str,
        error_msg: Optional[str] = None,
    ):
        """
        Update SMS status for a specific ticket event.
        event_type can be 'created', 'called', or 'completed'.
        """
        col_map = {
            "created": "sms_ticket_status",
            "called": "sms_called_status",
            "completed": "sms_completed_status",
        }
        col_name = col_map.get(event_type.lower())
        if not col_name:
            return

        with self._connect() as conn:
            cursor = conn.execute(
                f"UPDATE tickets SET {col_name} = ?, sms_last_error = ? WHERE ticket_number = ?",
                (status, error_msg, ticket_number),
            )
            if cursor.rowcount == 0:
                logger.warning(
                    "SMS status update matched no ticket (ticket_number=%s, event=%s, status=%s)",
                    ticket_number,
                    event_type,
                    status,
                )

    def get_ticket_sms_status(self, ticket_number: int) -> Dict[str, str]:
        """Retrieve delivery status flags for a ticket."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT sms_ticket_status, sms_called_status, sms_completed_status, sms_last_error
                FROM tickets WHERE ticket_number = ?
                """,
                (ticket_number,),
            ).fetchone()
            if not row:
                return {
                    "sms_ticket_status": "pending",
                    "sms_called_status": "pending",
                    "sms_completed_status": "pending",
                    "sms_last_error": None,
                }
            return {
                "sms_ticket_status": row["sms_ticket_status"] or "pending",
                "sms_called_status": row["sms_called_status"] or "pending",
                "sms_completed_status": row["sms_completed_status"] or "pending",
                "sms_last_error": row["sms_last_error"],
            }


_db_instance: Optional[DatabaseManager] = None


def get_database(db_file: Optional[Path | str] = None) -> DatabaseManager:
    """Get the singleton database instance, or a custom one if db_file provided."""
    global _db_instance
    if db_file is not None:
        return DatabaseManager(db_file)
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance
