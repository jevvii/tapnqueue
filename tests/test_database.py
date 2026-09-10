"""
Unit tests for TapNQue DatabaseManager.
Verifies ticket creation, queue priority, counter state machines, statistics, and clearing operations.
"""

import os
import tempfile
import unittest
from pathlib import Path

from tapnque.core.database import DatabaseManager


class TestDatabaseManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_kiosk.db"
        self.db = DatabaseManager(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initialization(self):
        """Verify default tables and initial counters."""
        counters = self.db.get_counters()
        self.assertEqual(len(counters), 3)
        self.assertEqual(counters[0]["name"], "Counter 1")
        self.assertEqual(counters[0]["status"], "available")

        stats = self.db.get_statistics()
        self.assertEqual(stats["total_served"], 0)
        self.assertEqual(stats["average_wait_time"], 0.0)

        settings = self.db.get_app_settings()
        self.assertTrue(settings["phone_number_enabled"])

    def test_create_ticket_sequential_numbering(self):
        """Verify tickets receive sequential numbers starting at 1."""
        t1 = self.db.create_ticket(
            name="Alice Smith",
            student_id="2023-00001",
            email="alice@example.com",
            phone="09123456789",
            purpose="Enrollment",
            visitor_type="Student",
        )
        t2 = self.db.create_ticket(
            name="Bob Jones",
            student_id="2023-00002",
            email="bob@example.com",
            phone="09987654321",
            purpose="Grades",
            visitor_type="Student",
        )
        self.assertEqual(t1["ticket_number"], 1)
        self.assertEqual(t2["ticket_number"], 2)

        queue = self.db.get_waiting_queue()
        self.assertEqual(len(queue), 2)
        self.assertEqual(queue[0]["ticket_number"], 1)
        self.assertEqual(queue[1]["ticket_number"], 2)

    def test_queue_priority_ordering(self):
        """Verify Urgent and High priorities leap ahead of Standard tickets."""
        self.db.create_ticket("Student 1", "2023-00001", "", "", "Inquiry", "Student")
        self.db.create_ticket("Student 2", "2023-00002", "", "", "Inquiry", "Student")
        self.db.create_ticket("Student 3", "2023-00003", "", "", "Inquiry", "Student")

        # Promote Student 3 to Urgent, Student 2 to High
        self.db.prioritize_waiting_ticket(3, "Urgent")
        self.db.prioritize_waiting_ticket(2, "High")

        queue = self.db.get_waiting_queue()
        self.assertEqual(queue[0]["ticket_number"], 3)  # Urgent first
        self.assertEqual(queue[1]["ticket_number"], 2)  # High second
        self.assertEqual(queue[2]["ticket_number"], 1)  # Standard third

        # Clear priority of Student 3
        self.db.clear_ticket_priority(3)
        queue_after = self.db.get_waiting_queue()
        self.assertEqual(queue_after[0]["ticket_number"], 2)  # High first
        self.assertEqual(queue_after[1]["ticket_number"], 1)  # Standard (ticket 1)
        self.assertEqual(queue_after[2]["ticket_number"], 3)  # Standard (ticket 3)

    def test_call_and_complete_lifecycle(self):
        """Verify ticket transitions: waiting -> serving -> completed."""
        ticket = self.db.create_ticket("Carlos", "2023-00010", "carlos@test.com", "", "Clearance")
        ticket_num = ticket["ticket_number"]

        # Call at Counter 1
        called = self.db.call_next_ticket(counter_id=1)
        self.assertIsNotNone(called)
        self.assertEqual(called["ticket_number"], ticket_num)
        self.assertEqual(called["status"], "serving")
        self.assertEqual(called["counter_id"], 1)

        # Counter should now be busy
        counter = self.db.get_counter(1)
        self.assertEqual(counter["status"], "busy")
        self.assertEqual(counter["current_ticket"], ticket_num)

        # Waiting queue is now empty
        self.assertEqual(len(self.db.get_waiting_queue()), 0)

        # Complete ticket
        result = self.db.mark_ticket_done(ticket_num)
        self.assertEqual(result["status"], "completed")

        # Counter becomes available
        counter = self.db.get_counter(1)
        self.assertEqual(counter["status"], "available")
        self.assertIsNone(counter["current_ticket"])

        # Stats should record 1 served ticket
        stats = self.db.get_statistics()
        self.assertEqual(stats["total_served"], 1)

    def test_clear_completed_tickets(self):
        """Verify clear_completed_tickets removes finished tickets but keeps waiting tickets."""
        self.db.create_ticket("Person 1", "001", "", "", "Test")
        self.db.create_ticket("Person 2", "002", "", "", "Test")

        # Complete Person 1
        self.db.call_next_ticket(1)
        self.db.mark_ticket_done(1)

        # Person 2 is still waiting
        self.assertEqual(len(self.db.get_waiting_queue()), 1)
        self.assertEqual(len(self.db.get_served_tickets()), 1)

        deleted = self.db.clear_completed_tickets()
        self.assertEqual(deleted, 1)

        # Served tickets list is now empty, waiting ticket untouched
        self.assertEqual(len(self.db.get_served_tickets()), 0)
        self.assertEqual(len(self.db.get_waiting_queue()), 1)

    def test_settings_toggle(self):
        """Verify phone number setting toggle persistence."""
        self.assertTrue(self.db.get_app_settings()["phone_number_enabled"])
        self.db.set_phone_number_enabled(False)
        self.assertFalse(self.db.get_app_settings()["phone_number_enabled"])
        self.db.set_phone_number_enabled(True)
        self.assertTrue(self.db.get_app_settings()["phone_number_enabled"])

    def test_telegram_settings_and_status(self):
        """Verify Telegram settings retrieval, saving, and ticket telegram status updates."""
        settings = self.db.get_telegram_settings()
        self.assertTrue(settings.get("telegram_enabled"))
        self.assertTrue(settings.get("telegram_mock_mode"))

        # Update settings
        self.db.save_telegram_settings(
            bot_token="123456:TEST_TOKEN",
            bot_username="CustomBot",
            template_created="Ticket #{ticket} created",
            template_called="Ticket #{ticket} called at Counter {counter}",
            template_completed="Ticket #{ticket} done",
        )
        updated = self.db.get_telegram_settings()
        self.assertEqual(updated["telegram_bot_token"], "123456:TEST_TOKEN")
        self.assertEqual(updated["telegram_bot_username"], "CustomBot")

        self.db.set_telegram_enabled(False)
        self.assertFalse(self.db.get_telegram_settings()["telegram_enabled"])
        self.db.set_telegram_enabled(True)

        self.db.set_telegram_mock_mode(False)
        self.assertFalse(self.db.get_telegram_settings()["telegram_mock_mode"])

        # Create ticket with telegram_chat_id
        ticket = self.db.create_ticket(
            name="John Doe",
            student_id="2023-12345",
            email="john@example.com",
            phone="09171234567",
            purpose="Enrollment",
            visitor_type="Student",
            telegram_chat_id="@johndoe",
        )
        self.assertEqual(ticket["telegram_chat_id"], "@johndoe")

        # Update telegram status
        self.db.update_ticket_telegram_status(ticket["ticket_number"], "created", "sent", None)
        status_info = self.db.get_ticket_telegram_status(ticket["ticket_number"])
        self.assertEqual(status_info["telegram_ticket_status"], "sent")


if __name__ == "__main__":
    unittest.main()
