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
    clear_mock_telegram_history,
    format_telegram_template,
    generate_telegram_qr_pixmap,
    get_mock_telegram_history,
    get_telegram_bot_link,
    send_ticket_called_telegram,
    send_ticket_completed_telegram,
    send_ticket_created_telegram,
    send_via_telegram_api,
    simulate_mock_telegram,
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
        from PySide6.QtWidgets import QApplication
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


if __name__ == "__main__":
    unittest.main()
