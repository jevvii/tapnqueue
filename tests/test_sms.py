"""
Unit tests for TapNQue Pure Software SMS Service (Tier 2).
Verifies phone number validation, template interpolation, mock simulation, and async queues.
"""

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tapnque.core.database import DatabaseManager, get_database
from tapnque.services import sms_service
from tapnque.services.sms_service import (
    clear_mock_sms_history,
    format_sms_template,
    get_mock_sms_history,
    is_valid_ph_mobile,
    sanitize_ph_phone_number,
    send_ticket_called_sms,
    send_ticket_completed_sms,
    send_ticket_created_sms,
    send_via_gateway,
    simulate_mock_sms,
)


def drain_sms_queue(timeout: float = 5.0):
    """Block until the background SMS worker has fully processed the queue.

    Prevents cross-test contamination: an undrained task could otherwise be
    processed after the next test's setUp clears the shared mock history.
    """
    deadline = time.time() + timeout
    while sms_service._queue_manager._queue.unfinished_tasks:
        if time.time() >= deadline:
            raise TimeoutError("SMS worker queue did not drain in time.")
        time.sleep(0.01)


class TestSMSService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_sms_kiosk.db"
        self.db = DatabaseManager(self.db_path)
        # Override singleton for tests
        import tapnque.core.database
        tapnque.core.database._db_instance = self.db
        clear_mock_sms_history()

    def tearDown(self):
        import tapnque.core.database
        tapnque.core.database._db_instance = None
        self.temp_dir.cleanup()
        clear_mock_sms_history()

    def test_phone_sanitization_valid_formats(self):
        """Verify various standard Philippine mobile formats sanitize to 09XXXXXXXXX."""
        cases = [
            ("09171234567", "09171234567"),
            ("0917-123-4567", "09171234567"),
            ("+639171234567", "09171234567"),
            ("639171234567", "09171234567"),
            ("9171234567", "09171234567"),
            ("(0918) 555-1234", "09185551234"),
            ("  0999 123 4567  ", "09991234567"),
            ("+63 920 111 2233", "09201112233"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(sanitize_ph_phone_number(raw), expected)
                self.assertTrue(is_valid_ph_mobile(raw))

    def test_phone_sanitization_invalid_formats(self):
        """Verify invalid or non-mobile inputs return None."""
        invalid_cases = [
            "",
            "   ",
            None,
            "12345",
            "08123456789",  # Does not start with 09
            "0917123456",   # 10 digits
            "091712345678", # 12 digits
            "abcdefghijk",
            "0917-ABC-1234",
            "+12025550199", # US number
        ]
        for raw in invalid_cases:
            with self.subTest(raw=raw):
                self.assertIsNone(sanitize_ph_phone_number(raw))
                self.assertFalse(is_valid_ph_mobile(raw))

    def test_template_interpolation(self):
        """Verify variable substitution in message templates."""
        template = "Ticket #{ticket} for {name} is at Counter {counter}. Purpose: {purpose}."
        context = {
            "ticket": 42,
            "name": "Juan Dela Cruz",
            "counter": 2,
            "purpose": "Enrollment",
        }
        formatted = format_sms_template(template, context)
        self.assertEqual(
            formatted,
            "Ticket #0042 for Juan Dela Cruz is at Counter 2. Purpose: Enrollment.",
        )

    def test_database_sms_settings_defaults_and_updates(self):
        """Verify SMS settings retrieval and persistence."""
        settings = self.db.get_sms_settings()
        self.assertIn("sms_enabled", settings)
        self.assertIn("sms_mock_mode", settings)
        self.assertIn("sms_api_key", settings)
        self.assertIn("sms_sender_name", settings)

        # Update settings
        self.db.update_sms_settings({
            "sms_enabled": False,
            "sms_mock_mode": True,
            "sms_api_key": "test_api_key_123",
            "sms_sender_name": "FatimaQueue",
        })
        updated = self.db.get_sms_settings()
        self.assertFalse(updated["sms_enabled"])
        self.assertTrue(updated["sms_mock_mode"])
        self.assertEqual(updated["sms_api_key"], "test_api_key_123")
        self.assertEqual(updated["sms_sender_name"], "FatimaQueue")

    def test_mock_sms_simulation_dispatch(self):
        """Verify Mock Simulation Mode writes history and returns mock_sent."""
        success, status, err = simulate_mock_sms(
            phone="09171234567",
            message="Your ticket is ready.",
            event_type="created",
            ticket_number=101,
        )
        self.assertTrue(success)
        self.assertEqual(status, "mock_sent")
        self.assertIsNone(err)

        history = get_mock_sms_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["phone"], "09171234567")
        self.assertEqual(history[0]["event_type"], "created")
        self.assertEqual(history[0]["ticket_number"], 101)

    def test_ticket_sms_status_tracking(self):
        """Verify ticket SMS delivery status updates in SQLite."""
        ticket = self.db.create_ticket(
            name="Maria Santos",
            student_id="2023-00099",
            email="maria@test.com",
            phone="09181234567",
            purpose="Permit",
            visitor_type="Student",
            phone_formatted="09181234567",
        )
        t_num = ticket["ticket_number"]

        status = self.db.get_ticket_sms_status(t_num)
        self.assertEqual(status["sms_ticket_status"], "pending")

        # Update created status
        self.db.update_ticket_sms_status(t_num, "created", "mock_sent")
        # Update called status
        self.db.update_ticket_sms_status(t_num, "called", "sent")
        # Update completed status
        self.db.update_ticket_sms_status(t_num, "completed", "sent")

        status_after = self.db.get_ticket_sms_status(t_num)
        self.assertEqual(status_after["sms_ticket_status"], "mock_sent")
        self.assertEqual(status_after["sms_called_status"], "sent")
        self.assertEqual(status_after["sms_completed_status"], "sent")

    def test_async_worker_end_to_end_mock(self):
        """Verify end-to-end async queuing for ticket lifecycle in Mock Mode."""
        # Enable SMS and Mock Mode
        self.db.update_sms_settings({"sms_enabled": True, "sms_mock_mode": True})

        ticket = self.db.create_ticket(
            name="Pedro Penduko",
            student_id="2023-00100",
            email="pedro@test.com",
            phone="09201234567",
            purpose="Grades",
            visitor_type="Student",
        )
        t_num = ticket["ticket_number"]

        # Trigger created SMS
        queued = send_ticket_created_sms(ticket, queue_position=1)
        self.assertTrue(queued)

        # Trigger called SMS
        queued_call = send_ticket_called_sms(ticket, counter_id=2)
        self.assertTrue(queued_call)

        # Trigger completed SMS
        queued_done = send_ticket_completed_sms(ticket)
        self.assertTrue(queued_done)

        # Wait until the worker has consumed every queued task
        drain_sms_queue()

        history = get_mock_sms_history()
        self.assertEqual(len(history), 3)
        events = [h["event_type"] for h in history]
        self.assertIn("created", events)
        self.assertIn("called", events)
        self.assertIn("completed", events)

        # Verify DB status updated
        status = self.db.get_ticket_sms_status(t_num)
        self.assertEqual(status["sms_ticket_status"], "mock_sent")
        self.assertEqual(status["sms_called_status"], "mock_sent")
        self.assertEqual(status["sms_completed_status"], "mock_sent")

    def test_disabled_sms_skips_dispatch(self):
        """Verify that when SMS is disabled, the worker logs 'disabled' status in DB."""
        self.db.set_sms_enabled(False)

        ticket = self.db.create_ticket(
            name="Clara Luna",
            student_id="2023-00555",
            email="clara@test.com",
            phone="09171112233",
            purpose="Permit",
            visitor_type="Student",
        )
        t_num = ticket["ticket_number"]

        queued = send_ticket_created_sms(ticket, queue_position=2)
        self.assertTrue(queued)
        drain_sms_queue()

        # No mock history should be recorded
        self.assertEqual(len(get_mock_sms_history()), 0)

        # DB status should record disabled
        status = self.db.get_ticket_sms_status(t_num)
        self.assertEqual(status["sms_ticket_status"], "disabled")

    def test_missing_or_invalid_phone_returns_false(self):
        """Verify triggers reject tickets without valid phone numbers without throwing errors."""
        no_phone_ticket = {
            "ticket_number": 88,
            "name": "Anonymous",
            "phone": "",
            "purpose": "Clearance",
        }
        self.assertFalse(send_ticket_created_sms(no_phone_ticket, 1))
        self.assertFalse(send_ticket_called_sms(no_phone_ticket, 1))
        self.assertFalse(send_ticket_completed_sms(no_phone_ticket))

        invalid_phone_ticket = {
            "ticket_number": 89,
            "name": "Invalid User",
            "phone": "12345",
            "purpose": "Clearance",
        }
        self.assertFalse(send_ticket_created_sms(invalid_phone_ticket, 1))
        self.assertFalse(send_ticket_called_sms(invalid_phone_ticket, 1))
        self.assertFalse(send_ticket_completed_sms(invalid_phone_ticket))

    def test_custom_templates_in_dispatch(self):
        """Verify that custom templates saved in the database are properly utilized in SMS messages."""
        self.db.update_sms_settings({
            "sms_enabled": True,
            "sms_mock_mode": True,
            "sms_template_created": "[FatimaQueue] Hi {name}! Your #{ticket} is pos {position}.",
            "sms_template_called": "[FatimaQueue] NOW SERVING #{ticket} at Counter {counter}!",
        })

        ticket = self.db.create_ticket(
            name="Jose Rizal",
            student_id="2023-00777",
            email="jose@test.com",
            phone="09191234567",
            purpose="Special Exam",
            visitor_type="Student",
        )

        send_ticket_created_sms(ticket, queue_position=5)
        send_ticket_called_sms(ticket, counter_id=3)
        drain_sms_queue()

        history = get_mock_sms_history()
        self.assertEqual(len(history), 2)
        self.assertIn("[FatimaQueue] Hi Jose Rizal! Your #0001 is pos 5.", history[0]["message"])
        self.assertIn("[FatimaQueue] NOW SERVING #0001 at Counter 3!", history[1]["message"])

    def test_completed_sms_respects_per_event_toggle(self):
        """Verify the optional Completed/Served SMS can be disabled independently."""
        self.db.update_sms_settings({
            "sms_enabled": True,
            "sms_mock_mode": True,
            "sms_completed_enabled": True,
        })

        ticket = self.db.create_ticket(
            name="Andres Bonifacio",
            student_id="2023-00888",
            email="andres@test.com",
            phone="09211234567",
            purpose="ID Claiming",
            visitor_type="Student",
        )

        # Enabled by default: dispatch is queued
        self.assertTrue(send_ticket_completed_sms(ticket))

        # Disabled via per-event setting: trigger is rejected before enqueue
        self.db.set_sms_completed_enabled(False)
        self.assertFalse(send_ticket_completed_sms(ticket))

        drain_sms_queue()
        history = get_mock_sms_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["event_type"], "completed")

        # Setting persists and re-enabling works
        self.db.set_sms_completed_enabled(True)
        self.assertTrue(self.db.get_sms_settings()["sms_completed_enabled"])
        self.assertTrue(send_ticket_completed_sms(ticket))
        drain_sms_queue()
        self.assertEqual(len(get_mock_sms_history()), 2)

    @patch("urllib.request.urlopen")
    def test_send_via_gateway_success(self, mock_urlopen):
        """Verify that send_via_gateway sends formatted POST request and parses response."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'[{"message_id": 12345, "status": "Queued"}]'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        success, status, body = send_via_gateway(
            phone="09171234567",
            message="Your ticket is ready.",
            api_key="valid_semaphore_key",
            sender_name="TapNQue",
        )

        self.assertTrue(success)
        self.assertEqual(status, "sent")
        self.assertIn("12345", body)

        # Inspect the Request object passed to urlopen
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), "POST")
        self.assertIn("semaphore.co/api/v4/messages", req.full_url)
        decoded_data = req.data.decode("utf-8")
        self.assertIn("apikey=valid_semaphore_key", decoded_data)
        self.assertIn("number=09171234567", decoded_data)
        self.assertIn("sendername=TapNQue", decoded_data)

    @patch("urllib.request.urlopen")
    def test_send_via_gateway_http_error(self, mock_urlopen):
        """Verify that HTTP error responses are caught and return (False, 'failed', err_msg)."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.semaphore.co/api/v4/messages",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=None,
        )

        success, status, err = send_via_gateway(
            phone="09171234567",
            message="Your ticket is ready.",
            api_key="bad_key",
            sender_name="TapNQue",
        )

        self.assertFalse(success)
        self.assertEqual(status, "failed")
        self.assertIn("401", err)


if __name__ == "__main__":
    unittest.main()
