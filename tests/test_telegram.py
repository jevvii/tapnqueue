"""
Unit tests for TapNQue Telegram Bot & QR Code Integration.
Verifies deep-link URL generation, QR pixmap generation, template interpolation,
mock dispatch simulation, HTTP API calls, and high-level triggers.
"""

import io
import json
import unittest
from unittest.mock import MagicMock, patch

from tapnque.services.telegram_service import (
    _link_listener,
    clear_mock_telegram_history,
    format_telegram_template,
    generate_telegram_qr_pixmap,
    get_mock_telegram_history,
    get_telegram_bot_link,
    parse_start_payload,
    send_ticket_called_telegram,
    send_ticket_completed_telegram,
    send_ticket_created_telegram,
    send_via_telegram_api,
    simulate_mock_telegram,
    validate_telegram_bot_token,
)


class TestTelegramService(unittest.TestCase):

    def setUp(self):
        clear_mock_telegram_history()

    def tearDown(self):
        clear_mock_telegram_history()

    def test_get_telegram_bot_link(self):
        """Verify deep-link formatting with and without ticket numbers."""
        link_base = get_telegram_bot_link()
        self.assertTrue(link_base.startswith("https://t.me/"))

        link_ticket = get_telegram_bot_link(42)
        self.assertTrue(link_ticket.endswith("?start=ticket_0042"))

    def test_format_telegram_template(self):
        """Verify dynamic placeholders {name}, {ticket}, {position}, {purpose}, {counter}."""
        template = "Hello {name}! Ticket #{ticket} is pos {position} for {purpose} at Counter {counter}."
        context = {
            "name": "Maria Clara",
            "ticket": 7,
            "position": 3,
            "purpose": "Enrollment",
            "counter": 2,
        }
        rendered = format_telegram_template(template, context)
        self.assertEqual(
            rendered,
            "Hello Maria Clara! Ticket #0007 is pos 3 for Enrollment at Counter 2.",
        )

    def test_generate_telegram_qr_pixmap(self):
        """Verify QR pixmap generation produces a valid pixmap or visual representation."""
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            self.skipTest("PySide6 not installed in current environment")
        app = QApplication.instance() or QApplication(["test", "-platform", "offscreen"])
        pixmap = generate_telegram_qr_pixmap(15, size=150)
        self.assertIsNotNone(pixmap)
        self.assertFalse(pixmap.isNull())
        self.assertEqual(pixmap.width(), 150)
        self.assertEqual(pixmap.height(), 150)

    def test_simulate_mock_telegram(self):
        """Verify mock dispatch records into history list."""
        self.assertEqual(len(get_mock_telegram_history()), 0)
        success, status, err = simulate_mock_telegram(
            chat_id="@testuser",
            text="Your ticket #0001 is ready!",
            event_type="called",
            ticket_number=1,
        )
        self.assertTrue(success)
        self.assertEqual(status, "mock_sent")
        self.assertIsNone(err)

        history = get_mock_telegram_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["chat_id"], "@testuser")
        self.assertEqual(history[0]["ticket_number"], 1)
        self.assertEqual(history[0]["event_type"], "called")

        clear_mock_telegram_history()
        self.assertEqual(len(get_mock_telegram_history()), 0)

    def test_send_via_telegram_api_missing_token(self):
        """Verify early failure when bot token is absent."""
        success, status, err = send_via_telegram_api("12345", "Test", "")
        self.assertFalse(success)
        self.assertEqual(status, "failed")
        self.assertIn("missing", err.lower())

    @patch("urllib.request.urlopen")
    def test_send_via_telegram_api_mocked_success(self, mock_urlopen):
        """Verify HTTP POST request formatting against Telegram Bot API."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"ok": True, "result": {"message_id": 999}}).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        success, status, body = send_via_telegram_api(
            chat_id="123456789",
            text="*Test Alert*",
            bot_token="TEST_BOT_TOKEN_123",
        )
        self.assertTrue(success)
        self.assertEqual(status, "sent")
        self.assertIn('"ok": true', body.lower())

        # Verify outgoing URL and payload
        self.assertTrue(mock_urlopen.called)
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "https://api.telegram.org/botTEST_BOT_TOKEN_123/sendMessage")
        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["chat_id"], "123456789")
        self.assertEqual(payload["text"], "*Test Alert*")
        self.assertEqual(payload["parse_mode"], "Markdown")

    def test_high_level_triggers_no_chat_id(self):
        """Verify triggers return False if ticket does not have a telegram_chat_id."""
        ticket = {"ticket_number": 1, "name": "Student", "purpose": "Help"}
        self.assertFalse(send_ticket_created_telegram(ticket, 1))
        self.assertFalse(send_ticket_called_telegram(ticket, 1))
        self.assertFalse(send_ticket_completed_telegram(ticket))

    def test_high_level_triggers_with_chat_id(self):
        """Verify triggers enqueue message when telegram_chat_id is present."""
        ticket = {
            "ticket_number": 5,
            "name": "Jane",
            "purpose": "Clearance",
            "telegram_chat_id": "@jane_student",
        }
        self.assertTrue(send_ticket_created_telegram(ticket, 2))
        self.assertTrue(send_ticket_called_telegram(ticket, 1))
        self.assertTrue(send_ticket_completed_telegram(ticket))


class TestTelegramDeepLinkAutomation(unittest.TestCase):
    """Tests for the zero-typing QR deep-link auto-link listener and bot validation."""

    def test_parse_start_payload(self):
        """Deep-link payloads from 'https://t.me/bot?start=ticket_XXXX' resolve to ticket numbers."""
        self.assertEqual(parse_start_payload("ticket_0042"), 42)
        self.assertEqual(parse_start_payload("ticket-7"), 7)
        self.assertEqual(parse_start_payload("TICKET_0001"), 1)
        self.assertEqual(parse_start_payload("42"), 42)
        self.assertIsNone(parse_start_payload("hello"))
        self.assertIsNone(parse_start_payload(""))
        self.assertIsNone(parse_start_payload(None))

    @patch("urllib.request.urlopen")
    def test_validate_bot_token_success(self, mock_urlopen):
        """getMe validation returns the auto-detected bot username."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"ok": True, "result": {"id": 1, "is_bot": True, "username": "TapNQueDemoBot"}}
        ).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        ok, username, err = validate_telegram_bot_token("123:ABC")
        self.assertTrue(ok)
        self.assertEqual(username, "TapNQueDemoBot")
        self.assertIsNone(err)
        self.assertIn("/bot123:ABC/getMe", mock_urlopen.call_args[0][0].full_url)

    @patch("urllib.request.urlopen")
    def test_validate_bot_token_invalid(self, mock_urlopen):
        """401 from Telegram produces a friendly invalid-token error."""
        import urllib.error

        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://api.telegram.org", 401, "Unauthorized", None, None
        )
        ok, username, err = validate_telegram_bot_token("bad-token")
        self.assertFalse(ok)
        self.assertIsNone(username)
        self.assertIn("Invalid bot token", err)

    def _make_db_and_ticket(self):
        import tempfile
        from pathlib import Path

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        from tapnque.core.database import DatabaseManager

        db = DatabaseManager(Path(tmp.name) / "listener_test.db")
        ticket = db.create_ticket(
            name="Ana Reyes",
            student_id="2023-00042",
            email="",
            phone="",
            purpose="Enrollment",
            visitor_type="Student",
        )
        return db, ticket

    def test_listener_start_with_ticket_payload_binds_chat(self):
        """'/start ticket_0007' binds the chat to the ticket and dispatches confirmation."""
        db, ticket = self._make_db_and_ticket()
        with patch("tapnque.services.telegram_service.get_database", return_value=db), patch(
            "tapnque.services.telegram_service.send_ticket_created_telegram", return_value=True
        ) as mock_send, patch(
            "tapnque.services.telegram_service.send_via_telegram_api", return_value=(True, "sent", None)
        ):
            _link_listener._handle_update(
                {
                    "update_id": 10,
                    "message": {
                        "text": f"/start ticket_{ticket['ticket_number']:04d}",
                        "chat": {"id": 555777, "first_name": "Ana"},
                    },
                }
            )

        stored = db.get_ticket_telegram_status(ticket["ticket_number"])
        self.assertEqual(stored["telegram_chat_id"], "555777")
        self.assertEqual(mock_send.call_count, 1)

    def test_listener_bare_start_sends_welcome(self):
        """A bare /start gets the onboarding guide; nothing is bound."""
        db, ticket = self._make_db_and_ticket()
        with patch("tapnque.services.telegram_service.get_database", return_value=db), patch(
            "tapnque.services.telegram_service.send_ticket_created_telegram", return_value=True
        ) as mock_send, patch(
            "tapnque.services.telegram_service.send_via_telegram_api", return_value=(True, "sent", None)
        ) as mock_api:
            _link_listener._handle_update(
                {
                    "update_id": 11,
                    "message": {"text": "/start", "chat": {"id": 888, "first_name": "New"}},
                }
            )

        stored = db.get_ticket_telegram_status(ticket["ticket_number"])
        self.assertIsNone(stored["telegram_chat_id"])
        self.assertEqual(mock_send.call_count, 0)
        self.assertEqual(mock_api.call_count, 1)
        self.assertIn("Welcome", mock_api.call_args[0][1])

    def test_recent_users_roster_survives_api_outage(self):
        """Contacts captured by the listener are served from cache when getUpdates fails."""
        from tapnque.services.telegram_service import fetch_recent_telegram_users

        db, ticket = self._make_db_and_ticket()
        with patch("tapnque.services.telegram_service.get_database", return_value=db), patch(
            "tapnque.services.telegram_service.send_via_telegram_api", return_value=(True, "sent", None)
        ):
            _link_listener._handle_update(
                {
                    "update_id": 20,
                    "message": {
                        "text": "/start",
                        "chat": {"id": 424242, "first_name": "Ria", "username": "riatest"},
                    },
                }
            )

        with patch("tapnque.services.telegram_service.get_database", return_value=db), patch(
            "urllib.request.urlopen", side_effect=OSError("no internet")
        ):
            users = fetch_recent_telegram_users("fake-token")

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["chat_id"], "424242")
        self.assertEqual(users[0]["username"], "riatest")

    def test_listener_repeat_start_is_idempotent(self):
        """Scanning twice never double-sends the confirmation alert."""
        db, ticket = self._make_db_and_ticket()
        update = {
            "update_id": 12,
            "message": {
                "text": f"/start ticket_{ticket['ticket_number']:04d}",
                "chat": {"id": 555777},
            },
        }
        with patch("tapnque.services.telegram_service.get_database", return_value=db), patch(
            "tapnque.services.telegram_service.send_ticket_created_telegram", return_value=True
        ) as mock_send, patch(
            "tapnque.services.telegram_service.send_via_telegram_api", return_value=(True, "sent", None)
        ):
            _link_listener._handle_update(dict(update))
            db.update_ticket_telegram_status(ticket["ticket_number"], "created", "sent")
            _link_listener._handle_update(dict(update, update_id=13))

        self.assertEqual(mock_send.call_count, 1)

    def test_robust_urlopen_ssl_retry(self):
        """Verify robust_urlopen retries with unverified context upon SSL verification error."""
        import ssl
        import urllib.error
        from tapnque.services.telegram_service import robust_urlopen

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"ok": true}'
        mock_response.__enter__.return_value = mock_response

        ssl_err = urllib.error.URLError(
            ssl.SSLCertVerificationError(
                "certificate verify failed: self-signed certificate in certificate chain"
            )
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = [ssl_err, mock_response]
            req = urllib.request.Request("https://api.telegram.org/bot123/getMe")
            resp = robust_urlopen(req)

            self.assertEqual(mock_urlopen.call_count, 2)
            # First call attempted verified context
            call1_ctx = mock_urlopen.call_args_list[0][1]["context"]
            self.assertTrue(call1_ctx.check_hostname)
            # Second call used unverified context
            call2_ctx = mock_urlopen.call_args_list[1][1]["context"]
            self.assertFalse(call2_ctx.check_hostname)
            self.assertEqual(call2_ctx.verify_mode, ssl.CERT_NONE)

    def test_render_qr_matrix_to_pixmap(self):
        """Verify render_qr_matrix_to_pixmap produces a valid QPixmap from a boolean matrix."""
        try:
            from PySide6.QtGui import QGuiApplication
        except ImportError:
            self.skipTest("PySide6 not installed in current environment")

        from tapnque.services.telegram_service import (
            generate_telegram_qr_pixmap,
            render_qr_matrix_to_pixmap,
        )

        _app = QGuiApplication.instance() or QGuiApplication(["test", "-platform", "offscreen"])
        matrix = [
            [True, False, True],
            [False, True, False],
            [True, True, True],
        ]
        pixmap = render_qr_matrix_to_pixmap(matrix, size=150)
        self.assertIsNotNone(pixmap)
        self.assertFalse(pixmap.isNull())
        self.assertEqual(pixmap.width(), 150)
        self.assertEqual(pixmap.height(), 150)

        # Test full deep link QR generation
        qr_pix = generate_telegram_qr_pixmap("https://t.me/OlfuTapNQue_bot", 200)
        self.assertIsNotNone(qr_pix)
        self.assertFalse(qr_pix.isNull())
        self.assertEqual(qr_pix.width(), 200)


if __name__ == "__main__":
    unittest.main()
