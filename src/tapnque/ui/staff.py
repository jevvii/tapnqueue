"""
Staff Admin UI - Service Desk Station.
Counter staff interface for calling tickets, recalling, and completing transactions.
"""

import sys
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tapnque.core.auth import require_admin_login
from tapnque.core.database import get_database
from tapnque.services.email_service import is_email_configured, send_called_email, send_served_email
from tapnque.services.sms_service import send_ticket_called_sms, send_ticket_completed_sms
from tapnque.ui.components.dialogs import HistoryDialog


class StaffAdmin(QWidget):
    """Main staff service desk interface."""

    def __init__(self, counter_id: int = 1):
        super().__init__()
        self.authenticated = require_admin_login("staff", "Staff Admin Login", self)
        if not self.authenticated:
            return

        self.db = get_database()
        self.service_counter_id = counter_id
        self.current_ticket = None
        self.history_dialog = None
        self._setup_ui()
        self._setup_timer()
        self._refresh_queue()

    def _setup_ui(self):
        self.setWindowTitle("Staff Admin - Service Desk")
        self.setMinimumSize(1280, 820)
        self.setStyleSheet(
            """
            QWidget {
                background: #eef3ef;
                color: #203126;
                font-family: "Segoe UI";
            }
            QLabel {
                background: transparent;
            }
            QFrame#topBar {
                background: #f7faf7;
                border: none;
            }
            QLabel#brandName {
                color: #0b9b4a;
                font-size: 27px;
                font-weight: 800;
            }
            QFrame#sidePanel {
                background: transparent;
            }
            QLabel#miniBrand {
                color: #0b9b4a;
                font-size: 22px;
                font-weight: 800;
            }
            QLabel#terminalName {
                color: #516257;
                font-size: 16px;
            }
            QPushButton#sideButton {
                background: transparent;
                color: #294032;
                border: 2px solid transparent;
                border-radius: 18px;
                padding: 20px 22px;
                text-align: left;
                font-size: 16px;
                font-weight: 600;
            }
            QPushButton#sideButton[active="true"] {
                background: #ffffff;
                color: #0b9b4a;
            }
            QFrame#card {
                background: #ffffff;
                border-radius: 34px;
                border: 1px solid #e3ebe3;
            }
            QLabel#cardTitle {
                color: #18241b;
                font-size: 38px;
                font-weight: 800;
            }
            QLabel#cardSubtitle {
                color: #55665a;
                font-size: 16px;
            }
            QFrame#statusPanel {
                background: #f6faf6;
                border: 1px solid #e3ebe3;
                border-radius: 24px;
            }
            QLabel#sectionLabel {
                color: #33483a;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#ticketDisplay {
                color: #0b9b4a;
                font-size: 44px;
                font-weight: 800;
            }
            QLabel#statusValue {
                color: #55665a;
                font-size: 18px;
                font-weight: 600;
            }
            QLabel#metricValue {
                color: #18241b;
                font-size: 26px;
                font-weight: 800;
            }
            QPushButton#primaryButton {
                background: #0a8c3c;
                color: white;
                border: none;
                border-radius: 18px;
                padding: 18px 20px;
                font-size: 18px;
                font-weight: 800;
            }
            QPushButton#primaryButton:hover {
                background: #087632;
            }
            QPushButton#primaryButton:pressed {
                background: #066229;
            }
            QPushButton#secondaryButton {
                background: #edf2ee;
                color: #294032;
                border: none;
                border-radius: 18px;
                padding: 18px 20px;
                font-size: 16px;
                font-weight: 700;
            }
            QPushButton#secondaryButton:hover {
                background: #e3ebe4;
            }
            QPushButton#secondaryButton:pressed {
                background: #d8e3da;
            }
            QPushButton:disabled {
                background: #d8e2da;
                color: #8a988e;
            }
            QTableWidget {
                background: #f6faf6;
                border: 1px solid #e3ebe3;
                border-radius: 20px;
                gridline-color: #e3ebe3;
                color: #203126;
                font-size: 14px;
            }
            QHeaderView::section {
                background: #edf2ee;
                color: #33483a;
                border: none;
                border-bottom: 1px solid #e3ebe3;
                padding: 14px 12px;
                font-size: 13px;
                font-weight: 700;
            }
            QTableWidget::item {
                padding: 12px;
            }
            QComboBox#counterSelector {
                background: #ffffff;
                color: #203126;
                border: 1px solid #d7e3d8;
                border-radius: 14px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 700;
            }
            """
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(86)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(42, 18, 42, 18)
        top_layout.setSpacing(16)

        brand_name = QLabel("TapNQue")
        brand_name.setObjectName("brandName")
        top_layout.addWidget(brand_name)
        top_layout.addStretch()

        counter_label = QLabel("Station:")
        counter_label.setStyleSheet("font-weight: 700; color: #33483a;")
        top_layout.addWidget(counter_label)

        self.counter_combo = QComboBox()
        self.counter_combo.setObjectName("counterSelector")
        self.counter_combo.addItems(["Counter 1", "Counter 2", "Counter 3"])
        self.counter_combo.setCurrentIndex(max(0, min(2, self.service_counter_id - 1)))
        self.counter_combo.currentIndexChanged.connect(self._on_counter_changed)
        top_layout.addWidget(self.counter_combo)

        root_layout.addWidget(top_bar)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(28, 18, 32, 32)
        body_layout.setSpacing(30)
        root_layout.addWidget(body)

        side_panel = QFrame()
        side_panel.setObjectName("sidePanel")
        side_panel.setFixedWidth(270)
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(10, 8, 10, 12)
        side_layout.setSpacing(22)

        side_layout.addSpacing(8)

        side_brand = QLabel("TapNQue")
        side_brand.setObjectName("miniBrand")
        side_layout.addWidget(side_brand)

        self.side_terminal = QLabel(f"Staff Service Desk - Counter {self.service_counter_id}")
        self.side_terminal.setObjectName("terminalName")
        side_layout.addWidget(self.side_terminal)

        side_layout.addSpacing(28)

        dashboard_button = QPushButton("->  Queue Control")
        dashboard_button.setObjectName("sideButton")
        dashboard_button.setProperty("active", True)
        side_layout.addWidget(dashboard_button)
        side_layout.addStretch()

        body_layout.addWidget(side_panel, 0, Qt.AlignTop)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(76, 56, 76, 48)
        card_layout.setSpacing(24)

        title = QLabel("Queue Control Center")
        title.setObjectName("cardTitle")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("Manage the next ticket, monitor the queue, and complete service from one screen.")
        subtitle.setObjectName("cardSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        card_layout.addWidget(subtitle)

        status_panel = QFrame()
        status_panel.setObjectName("statusPanel")
        status_layout = QHBoxLayout(status_panel)
        status_layout.setContentsMargins(28, 24, 28, 24)
        status_layout.setSpacing(32)

        current_col = QVBoxLayout()
        current_col.setSpacing(6)
        current_label = QLabel("CURRENT TICKET")
        current_label.setObjectName("sectionLabel")
        self.ticket_display = QLabel("--")
        self.ticket_display.setObjectName("ticketDisplay")
        self.ticket_display.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_value = QLabel("Waiting for next call")
        self.status_value.setObjectName("statusValue")
        current_col.addWidget(current_label)
        current_col.addWidget(self.ticket_display)
        current_col.addWidget(self.status_value)
        current_col.addStretch()
        status_layout.addLayout(current_col, 2)

        waiting_col = QVBoxLayout()
        waiting_col.setSpacing(6)
        waiting_label = QLabel("WAITING NOW")
        waiting_label.setObjectName("sectionLabel")
        self.waiting_value = QLabel("0")
        self.waiting_value.setObjectName("metricValue")
        waiting_col.addWidget(waiting_label)
        waiting_col.addWidget(self.waiting_value)
        waiting_col.addStretch()
        status_layout.addLayout(waiting_col, 1)

        serving_col = QVBoxLayout()
        serving_col.setSpacing(6)
        serving_label = QLabel("IN SERVICE")
        serving_label.setObjectName("sectionLabel")
        self.serving_value = QLabel("0")
        self.serving_value.setObjectName("metricValue")
        serving_col.addWidget(serving_label)
        serving_col.addWidget(self.serving_value)
        serving_col.addStretch()
        status_layout.addLayout(serving_col, 1)

        card_layout.addWidget(status_panel)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(16)

        self.call_btn = QPushButton("CALL NEXT")
        self.call_btn.setObjectName("primaryButton")
        self.call_btn.clicked.connect(self._call_next)
        action_layout.addWidget(self.call_btn)

        self.recall_btn = QPushButton("RECALL")
        self.recall_btn.setObjectName("secondaryButton")
        self.recall_btn.setEnabled(False)
        self.recall_btn.clicked.connect(self._recall_ticket)
        action_layout.addWidget(self.recall_btn)

        self.done_btn = QPushButton("MARK AS DONE")
        self.done_btn.setObjectName("secondaryButton")
        self.done_btn.setEnabled(False)
        self.done_btn.clicked.connect(self._mark_done)
        action_layout.addWidget(self.done_btn)

        self.refresh_btn = QPushButton("REFRESH")
        self.refresh_btn.setObjectName("secondaryButton")
        self.refresh_btn.clicked.connect(self._refresh_queue)
        action_layout.addWidget(self.refresh_btn)

        self.history_btn = QPushButton("HISTORY")
        self.history_btn.setObjectName("secondaryButton")
        self.history_btn.clicked.connect(self._show_history)
        action_layout.addWidget(self.history_btn)

        card_layout.addLayout(action_layout)

        queue_label = QLabel("WAITING QUEUE")
        queue_label.setObjectName("sectionLabel")
        card_layout.addWidget(queue_label)

        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(8)
        self.queue_table.setHorizontalHeaderLabels(
            ["Ticket #", "Name", "Student ID", "Visitor", "Phone", "Purpose", "Priority", "Wait Time"]
        )
        self.queue_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.queue_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.queue_table.setAlternatingRowColors(False)
        self.queue_table.setMinimumHeight(300)
        self.queue_table.verticalHeader().setVisible(False)
        self.queue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.queue_table.horizontalHeader().setMinimumSectionSize(120)
        card_layout.addWidget(self.queue_table)

        body_layout.addWidget(card, 1)

    def _on_counter_changed(self, index: int):
        self.service_counter_id = index + 1
        self.side_terminal.setText(f"Staff Service Desk - Counter {self.service_counter_id}")
        self._refresh_queue()

    def _setup_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_queue)
        self.refresh_timer.start(3000)

    def _call_next(self):
        ticket = self.db.call_next_ticket(self.service_counter_id)
        if not ticket:
            QMessageBox.information(self, "Queue Empty", "No tickets in the waiting queue.")
            return

        self.current_ticket = ticket["ticket_number"]
        if ticket.get("email") and is_email_configured():
            send_called_email(
                to_email=ticket["email"],
                student_name=ticket.get("name", "Student"),
                ticket_number=ticket["ticket_number"],
                reason=ticket.get("purpose", ""),
                counter_id=self.service_counter_id,
                async_send=True,
            )
        send_ticket_called_sms(ticket, self.service_counter_id)
        self._refresh_queue()

    def _recall_ticket(self):
        if not self.current_ticket:
            return

        self.db.recall_ticket(self.current_ticket)
        active_ticket = next(
            (
                ticket
                for ticket in self.db.get_currently_serving()
                if ticket.get("ticket_number") == self.current_ticket
            ),
            None,
        )
        if active_ticket and active_ticket.get("email") and is_email_configured():
            send_called_email(
                to_email=active_ticket["email"],
                student_name=active_ticket.get("name", "Student"),
                ticket_number=active_ticket["ticket_number"],
                reason=active_ticket.get("purpose", ""),
                counter_id=self.service_counter_id,
                async_send=True,
            )
        if active_ticket:
            send_ticket_called_sms(active_ticket, self.service_counter_id)
        self._refresh_queue()

    def _mark_done(self):
        if not self.current_ticket:
            return

        active_ticket = next(
            (
                ticket
                for ticket in self.db.get_currently_serving()
                if ticket.get("ticket_number") == self.current_ticket
            ),
            None,
        )

        self.db.mark_ticket_done(self.current_ticket)
        if active_ticket and active_ticket.get("email") and is_email_configured():
            send_served_email(
                to_email=active_ticket["email"],
                student_name=active_ticket.get("name", "Student"),
                ticket_number=active_ticket["ticket_number"],
                reason=active_ticket.get("purpose", ""),
                async_send=True,
            )
        if active_ticket:
            send_ticket_completed_sms(active_ticket)
        self.current_ticket = None
        self._refresh_queue()

    def _show_history(self):
        if self.history_dialog is None:
            self.history_dialog = HistoryDialog(self)

        history = list(reversed(self.db.get_served_tickets()[-30:]))
        self.history_dialog.update_history(history)
        self.history_dialog.show()
        self.history_dialog.raise_()
        self.history_dialog.activateWindow()

    def _priority_for_visitor(self, visitor_type: str):
        visitor = (visitor_type or "").strip().lower()
        if visitor == "pwd":
            return "High Priority", QColor("#c0392b")
        if visitor in {"parent", "guardian"}:
            return "Priority", QColor("#e67e22")
        if visitor == "student":
            return "Standard", QColor("#1f6feb")
        return "Standard", QColor("#7f8c8d")

    def _refresh_queue(self):
        try:
            waiting = self.db.get_waiting_queue()
            serving = self.db.get_currently_serving()
            history = self.db.get_served_tickets()

            active_ticket = next(
                (ticket for ticket in serving if ticket.get("counter_id") == self.service_counter_id),
                None,
            )

            self.queue_table.setRowCount(len(waiting))
            for row, ticket in enumerate(waiting):
                self.queue_table.setItem(row, 0, QTableWidgetItem(f"#{ticket['ticket_number']:04d}"))
                self.queue_table.setItem(row, 1, QTableWidgetItem(ticket.get("name", "")))
                self.queue_table.setItem(row, 2, QTableWidgetItem(ticket.get("student_id", "")))
                self.queue_table.setItem(row, 3, QTableWidgetItem(ticket.get("visitor_type", "")))
                self.queue_table.setItem(row, 4, QTableWidgetItem(ticket.get("phone", "")))
                self.queue_table.setItem(row, 5, QTableWidgetItem(ticket.get("purpose", "")))
                priority_label, priority_color = self._priority_for_visitor(ticket.get("visitor_type", ""))
                priority_item = QTableWidgetItem(priority_label)
                priority_item.setForeground(priority_color)
                self.queue_table.setItem(row, 6, priority_item)

                try:
                    created = datetime.fromisoformat(ticket["created_at"])
                    wait_seconds = (datetime.now() - created).total_seconds()
                    wait_minutes = max(0, int(wait_seconds / 60))
                    self.queue_table.setItem(row, 7, QTableWidgetItem(f"{wait_minutes} min"))
                except Exception:
                    self.queue_table.setItem(row, 7, QTableWidgetItem("0 min"))

            self.waiting_value.setText(str(len(waiting)))
            self.serving_value.setText(str(len(serving)))

            if active_ticket:
                self.current_ticket = active_ticket["ticket_number"]
                self.ticket_display.setText(f"#{active_ticket['ticket_number']:04d}")
                self.status_value.setText(active_ticket.get("status", "Serving").capitalize())
                self.call_btn.setEnabled(False)
                self.recall_btn.setEnabled(True)
                self.done_btn.setEnabled(True)
            else:
                self.current_ticket = None
                self.ticket_display.setText("--")
                self.status_value.setText(f"Waiting for Counter {self.service_counter_id} call")
                self.call_btn.setEnabled(True)
                self.recall_btn.setEnabled(False)
                self.done_btn.setEnabled(False)

            if self.history_dialog is not None and self.history_dialog.isVisible():
                self.history_dialog.update_history(list(reversed(history[-30:])))

        except Exception as e:
            print(f"Error refreshing queue: {e}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = StaffAdmin()
    if getattr(window, "authenticated", False):
        window.show()
    else:
        sys.exit(0)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
