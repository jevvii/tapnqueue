import logging
from datetime import datetime
from typing import List, Dict, Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from tapnque.config import get_asset_path
from tapnque.core.database import get_database
from tapnque.services.telegram_service import generate_telegram_qr_pixmap
from tapnque.ui.components.animations import WaitingSignalAnimation

logger = logging.getLogger("tapnque.dialogs")


class TicketCreatedDialog(QDialog):
    """Branded success modal shown after student registration.

    Features:
    - Adaptive layout with the Telegram QR code positioned as the Hero centerpiece.
    - Automatic 30-second countdown timer with live UI countdown display.
    - Real-time polling to detect successful QR scan and close the dialog immediately.
    """

    def __init__(
        self,
        ticket: Dict[str, Any],
        queue_position: int,
        purpose: str,
        email_sent: bool = False,
        sms_sent: bool = False,
        telegram_sent: bool = False,
        telegram_offered: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.ticket = ticket
        self.queue_position = queue_position
        self.purpose = purpose
        self.email_sent = email_sent
        self.sms_sent = sms_sent
        self.telegram_sent = telegram_sent
        self.telegram_offered = telegram_offered
        self.logo_source = get_asset_path("OLFU LOGO 1.png")

        self.db = get_database()
        self.ticket_number = ticket.get("ticket_number", 0)
        self.remaining_seconds = 30
        self._is_closing = False

        self._setup_ui()
        self._finalize_sizing()

        # 30-second countdown timer
        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self._on_countdown_tick)
        self.countdown_timer.start()

        # Fast background poller to detect QR scan completion immediately
        if self.telegram_offered:
            self.scan_poll_timer = QTimer(self)
            self.scan_poll_timer.setInterval(400)
            self.scan_poll_timer.timeout.connect(self._check_qr_scanned)
            self.scan_poll_timer.start()

    def _on_countdown_tick(self):
        self.remaining_seconds -= 1
        self._update_countdown_display()
        if self.remaining_seconds <= 0:
            self._stop_timers()
            self.accept()

    def _update_countdown_display(self):
        if hasattr(self, "auto_close_hint") and self.auto_close_hint is not None:
            self.auto_close_hint.setText(
                f"⏱️ This screen closes automatically in {self.remaining_seconds}s"
            )
        if hasattr(self, "done_button") and self.done_button is not None:
            self.done_button.setText(f"DONE ({self.remaining_seconds}s)")

    def _check_qr_scanned(self):
        if not self.telegram_offered or self._is_closing:
            return
        try:
            status = self.db.get_ticket_telegram_status(self.ticket_number)
            if status and status.get("telegram_chat_id"):
                logger.info(
                    "QR scan verified for ticket #%04d (Chat ID: %s). Closing screen immediately.",
                    self.ticket_number,
                    status.get("telegram_chat_id"),
                )
                self._stop_timers()
                self._is_closing = True
                if hasattr(self, "scan_status_pill") and self.scan_status_pill is not None:
                    self.scan_status_pill.setText("✅ QR Scanned! Connecting...")
                    self.scan_status_pill.setStyleSheet(
                        "background: #105938; color: #ffffff; border: 1px solid #4dd38a; "
                        "border-radius: 12px; padding: 6px 14px; font-size: 12px; font-weight: 800;"
                    )
                self.accept()
        except Exception as exc:
            logger.debug("Error checking QR scan status: %s", exc)

    def _stop_timers(self):
        if hasattr(self, "countdown_timer") and self.countdown_timer.isActive():
            self.countdown_timer.stop()
        if hasattr(self, "scan_poll_timer") and self.scan_poll_timer.isActive():
            self.scan_poll_timer.stop()

    def accept(self):
        self._stop_timers()
        super().accept()

    def reject(self):
        self._stop_timers()
        super().reject()

    def closeEvent(self, event):
        self._stop_timers()
        super().closeEvent(event)

    def _setup_ui(self):
        self.setWindowTitle("Ticket Created")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setStyleSheet(
            """
            TicketCreatedDialog {
                background: transparent;
                font-family: "Segoe UI", "Noto Sans", "DejaVu Sans", sans-serif;
            }
            QFrame#dialogCard {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #071912,
                    stop: 0.55 #0a2417,
                    stop: 1 #123223
                );
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 34px;
            }
            QFrame#ticketBadge {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 28px;
            }
            QFrame#detailPanel {
                background: rgba(247, 251, 248, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 24px;
            }
            QFrame#telegramHeroCard {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #f7fdf9,
                    stop: 1 #eef8f2
                );
                border: 2px solid #4dd38a;
                border-radius: 28px;
            }
            QFrame#qrHeroFrame {
                background: #ffffff;
                border: 2px solid #cce8d6;
                border-radius: 20px;
            }
            QLabel#eyebrow {
                color: rgba(145, 226, 179, 0.92);
                font-size: 14px;
                font-weight: 800;
                letter-spacing: 3px;
            }
            QLabel#dialogTitle {
                color: #f4fbf6;
                font-size: 32px;
                font-weight: 900;
            }
            QLabel#dialogCopy {
                color: rgba(230, 240, 234, 0.86);
                font-size: 16px;
            }
            QLabel#ticketNumber {
                color: #ffffff;
                font-size: 54px;
                font-weight: 900;
            }
            QLabel#ticketLabel {
                color: rgba(189, 224, 201, 0.86);
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 3px;
            }
            QLabel#waitTitle {
                color: #f7fff8;
                font-size: 24px;
                font-weight: 900;
            }
            QLabel#waitCopy {
                color: rgba(224, 235, 228, 0.8);
                font-size: 15px;
            }
            QLabel#metaValue {
                color: #ffffff;
                font-size: 24px;
                font-weight: 800;
            }
            QLabel#metaLabel {
                color: rgba(185, 212, 194, 0.72);
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 2px;
            }
            QLabel#statusPill {
                background: rgba(77, 211, 138, 0.16);
                color: #9ff1bf;
                border: 1px solid rgba(77, 211, 138, 0.35);
                border-radius: 16px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#tgCardTag {
                color: #0d7045;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 2px;
            }
            QLabel#tgCardTitle {
                color: #083822;
                font-size: 16px;
                font-weight: 900;
            }
            QLabel#tgStep {
                color: #1b3d2b;
                font-size: 12px;
                font-weight: 700;
            }
            QLabel#scanStatusPill {
                background: rgba(13, 112, 69, 0.12);
                color: #0d7045;
                border: 1px solid rgba(13, 112, 69, 0.3);
                border-radius: 12px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 800;
            }
            QPushButton#doneButton {
                background: #4dd38a;
                color: #082114;
                border: none;
                border-radius: 18px;
                padding: 14px 26px;
                font-size: 17px;
                font-weight: 900;
            }
            QPushButton#doneButton:hover {
                background: #62e39b;
            }
            """
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setObjectName("dialogCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 26, 30, 24)
        card_layout.setSpacing(18)

        top_row = QHBoxLayout()
        top_row.setSpacing(18)

        logo_label = QLabel()
        logo_pixmap = QPixmap(str(self.logo_source))
        if not logo_pixmap.isNull():
            logo_label.setPixmap(
                logo_pixmap.scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        logo_label.setFixedSize(56, 56)
        logo_label.setAlignment(Qt.AlignCenter)
        top_row.addWidget(logo_label, 0, Qt.AlignTop)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        eyebrow = QLabel("TICKET CONFIRMED")
        eyebrow.setObjectName("eyebrow")
        title_col.addWidget(eyebrow)

        title = QLabel("Please wait for your number to be called")
        title.setObjectName("dialogTitle")
        title.setWordWrap(True)
        title_col.addWidget(title)

        copy = QLabel(
            "Your queue request has been saved. Stay near the display monitor and listen for your ticket number."
        )
        copy.setObjectName("dialogCopy")
        copy.setWordWrap(True)
        title_col.addWidget(copy)
        top_row.addLayout(title_col, 1)
        card_layout.addLayout(top_row)

        center_row = QHBoxLayout()
        center_row.setSpacing(20)

        badge = self._build_ticket_badge()
        center_row.addWidget(badge, 2 if self.telegram_offered else 1)

        if self.telegram_offered:
            telegram_card = self._build_telegram_card()
            if telegram_card is not None:
                center_row.addWidget(telegram_card, 3)

        center_row.addWidget(self._build_detail_panel(), 2 if self.telegram_offered else 1)
        card_layout.addLayout(center_row)

        footer_row = QHBoxLayout()
        footer_row.setSpacing(16)

        self.auto_close_hint = QLabel("⏱️ This screen closes automatically in 30s")
        self.auto_close_hint.setObjectName("autoCloseHint")
        self.auto_close_hint.setStyleSheet(
            "color: rgba(189, 224, 201, 0.85); font-size: 13px; font-weight: 700;"
        )
        footer_row.addWidget(self.auto_close_hint, 1)

        self.done_button = QPushButton("DONE (30s)")
        self.done_button.setObjectName("doneButton")
        self.done_button.setCursor(Qt.PointingHandCursor)
        self.done_button.clicked.connect(self.accept)
        footer_row.addWidget(self.done_button)
        card_layout.addLayout(footer_row)

        root_layout.addWidget(card)

    def _build_ticket_badge(self) -> QFrame:
        """Left panel displaying ticket number, purpose, and position."""
        badge = QFrame()
        badge.setObjectName("ticketBadge")
        badge_layout = QVBoxLayout(badge)
        badge_layout.setContentsMargins(24, 20, 24, 20)
        badge_layout.setSpacing(8)

        ticket_label = QLabel("YOUR TICKET")
        ticket_label.setObjectName("ticketLabel")
        ticket_label.setAlignment(Qt.AlignCenter)
        badge_layout.addWidget(ticket_label)

        ticket_number = QLabel(f"#{self.ticket['ticket_number']:04d}")
        ticket_number.setObjectName("ticketNumber")
        ticket_number.setAlignment(Qt.AlignCenter)
        badge_layout.addWidget(ticket_number)

        purpose_label = QLabel(self.purpose)
        purpose_label.setObjectName("dialogCopy")
        purpose_label.setAlignment(Qt.AlignCenter)
        badge_layout.addWidget(purpose_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(255, 255, 255, 0.12); margin: 6px 0;")
        badge_layout.addWidget(sep)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(12)
        meta_row.addWidget(self._build_meta_block(str(self.queue_position), "QUEUE POSITION"))
        meta_row.addWidget(
            self._build_meta_block(self.ticket.get("visitor_type", "Student"), "VISITOR TYPE")
        )
        badge_layout.addLayout(meta_row)

        badge_layout.addStretch(1)
        return badge

    def _build_telegram_card(self) -> "QFrame | None":
        """Hero scan-to-link QR centerpiece with instant scanning and live connection status."""
        qr_pixmap = generate_telegram_qr_pixmap(self.ticket["ticket_number"], size=210)
        if qr_pixmap is None or qr_pixmap.isNull():
            return None

        card = QFrame()
        card.setObjectName("telegramHeroCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(8)

        tag_label = QLabel("📱 INSTANT PHONE NOTIFICATIONS")
        tag_label.setObjectName("tgCardTag")
        tag_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(tag_label)

        title = QLabel("SCAN FOR REAL-TIME ALERTS")
        title.setObjectName("tgCardTitle")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        qr_frame = QFrame()
        qr_frame.setObjectName("qrHeroFrame")
        qr_frame_layout = QVBoxLayout(qr_frame)
        qr_frame_layout.setContentsMargins(8, 8, 8, 8)
        qr_frame_layout.setAlignment(Qt.AlignCenter)

        qr_img = QLabel()
        qr_img.setPixmap(qr_pixmap)
        qr_img.setAlignment(Qt.AlignCenter)
        qr_img.setFixedSize(210, 210)
        qr_frame_layout.addWidget(qr_img)
        card_layout.addWidget(qr_frame, 0, Qt.AlignCenter)

        # Allow clicking QR to simulate scan during defense demo or testing
        qr_frame.setCursor(Qt.PointingHandCursor)

        def _on_qr_click(event):
            del event
            try:
                settings = self.db.get_telegram_settings()
                is_mock = settings.get("telegram_mock_mode", True)
                if is_mock or not settings.get("telegram_bot_token"):
                    self.db.bind_telegram_chat_id(self.ticket_number, "mock_student_scan")
                    from tapnque.services.telegram_service import send_ticket_created_telegram

                    linked_ticket = dict(self.ticket)
                    linked_ticket["telegram_chat_id"] = "mock_student_scan"
                    send_ticket_created_telegram(linked_ticket, self.queue_position)
                    logger.info("Mock QR scan simulated on click for ticket #%04d", self.ticket_number)
            except Exception as exc:
                logger.debug("QR click trigger exception: %s", exc)
            self._check_qr_scanned()

        qr_frame.mousePressEvent = _on_qr_click

        steps = QLabel("1. Point camera at QR  •  2. Tap START in Telegram")
        steps.setObjectName("tgStep")
        steps.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(steps)

        self.scan_status_pill = QLabel("🟢 Scanner active • Waiting for scan...")
        self.scan_status_pill.setObjectName("scanStatusPill")
        self.scan_status_pill.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.scan_status_pill, 0, Qt.AlignCenter)

        card_layout.addStretch(1)
        return card

    def _build_detail_panel(self) -> QFrame:
        """Right panel displaying waiting queue guidance and status."""
        detail_panel = QFrame()
        detail_panel.setObjectName("detailPanel")
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(24, 20, 24, 20)
        detail_layout.setSpacing(10)

        wait_title = QLabel("Now in waiting queue")
        wait_title.setObjectName("waitTitle")
        wait_title.setWordWrap(True)
        detail_layout.addWidget(wait_title)

        signal_animation = WaitingSignalAnimation()
        detail_layout.addWidget(signal_animation, 0, Qt.AlignLeft)

        wait_copy = QLabel("Please watch the lobby display and listen for your number.")
        wait_copy.setObjectName("waitCopy")
        wait_copy.setWordWrap(True)
        detail_layout.addWidget(wait_copy)

        if not self.telegram_offered:
            meta_row = QHBoxLayout()
            meta_row.setSpacing(18)
            meta_row.addWidget(self._build_meta_block(str(self.queue_position), "QUEUE POSITION"))
            meta_row.addWidget(
                self._build_meta_block(self.ticket.get("visitor_type", "Student"), "VISITOR TYPE")
            )
            detail_layout.addLayout(meta_row)

        status_notes = []
        if self.email_sent:
            status_notes.append("Email sent")
        if self.sms_sent:
            status_notes.append("SMS dispatched")
        if self.telegram_sent:
            status_notes.append("Telegram alert sent")
        if status_notes:
            status_text = " • ".join(status_notes) + " successfully."
        elif self.telegram_offered:
            status_text = "Free Telegram alerts active on scan."
        else:
            status_text = "Digital ticket ready on this screen."
        status_pill = QLabel(status_text)
        status_pill.setObjectName("statusPill")
        status_pill.setAlignment(Qt.AlignCenter)
        status_pill.setWordWrap(True)
        detail_layout.addWidget(status_pill, 0, Qt.AlignLeft)

        detail_layout.addStretch(1)
        return detail_panel

    def _finalize_sizing(self):
        """Size the dialog from its content, clamped to the usable screen."""
        self.adjustSize()
        width, height = self.width(), self.height()
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            width = min(width, int(available.width() * 0.94))
            height = min(height, int(available.height() * 0.92))
        min_w = 980 if self.telegram_offered else 840
        min_h = 580
        self.resize(max(width, min_w), max(height, min_h))
        self.setMinimumSize(min_w, min_h)

    def _build_meta_block(self, value: str, label_text: str):
        block = QFrame()
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        value_label = QLabel(value)
        value_label.setObjectName("metaValue")
        layout.addWidget(value_label)

        text_label = QLabel(label_text)
        text_label.setObjectName("metaLabel")
        layout.addWidget(text_label)
        return block

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(4, 12, 8, 155))


class HistoryDialog(QDialog):
    """Popup window for viewing completed and recent queue ticket history."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ticket History")
        self.setMinimumSize(920, 520)
        self.setModal(False)
        self.setStyleSheet(
            """
            QDialog {
                background: #eef3ef;
                color: #203126;
                font-family: "Segoe UI";
            }
            QFrame#dialogCard {
                background: #ffffff;
                border-radius: 28px;
                border: 1px solid #e3ebe3;
            }
            QLabel#dialogTitle {
                color: #18241b;
                font-size: 28px;
                font-weight: 800;
            }
            QLabel#dialogSubtitle {
                color: #55665a;
                font-size: 15px;
            }
            QLabel#sectionLabel {
                color: #33483a;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton#secondaryButton {
                background: #edf2ee;
                color: #294032;
                border: none;
                border-radius: 18px;
                padding: 14px 18px;
                font-size: 15px;
                font-weight: 700;
            }
            QPushButton#secondaryButton:hover {
                background: #e3ebe4;
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
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)

        card = QFrame()
        card.setObjectName("dialogCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(18)

        title = QLabel("Ticket History")
        title.setObjectName("dialogTitle")
        card_layout.addWidget(title)

        subtitle = QLabel("Recent queue activity with ticket details, date, and time.")
        subtitle.setObjectName("dialogSubtitle")
        card_layout.addWidget(subtitle)

        label = QLabel("RECENT ACTIVITY")
        label.setObjectName("sectionLabel")
        card_layout.addWidget(label)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(9)
        self.history_table.setHorizontalHeaderLabels(
            ["Ticket #", "Name", "Student ID", "Visitor", "Phone", "Purpose", "Status", "Date", "Time"]
        )
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setAlternatingRowColors(False)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.horizontalHeader().setMinimumSectionSize(110)
        card_layout.addWidget(self.history_table)

        button_row = QHBoxLayout()
        button_row.addStretch()

        close_button = QPushButton("CLOSE")
        close_button.setObjectName("secondaryButton")
        close_button.clicked.connect(self.close)
        button_row.addWidget(close_button)

        card_layout.addLayout(button_row)
        layout.addWidget(card)

    def update_history(self, history_rows: List[Dict[str, Any]]):
        """Populate the history table with tickets."""
        self.history_table.setRowCount(len(history_rows))
        for row, ticket in enumerate(history_rows):
            self.history_table.setItem(row, 0, QTableWidgetItem(f"#{ticket['ticket_number']:04d}"))
            self.history_table.setItem(row, 1, QTableWidgetItem(ticket.get("name", "")))
            self.history_table.setItem(row, 2, QTableWidgetItem(ticket.get("student_id", "")))
            self.history_table.setItem(row, 3, QTableWidgetItem(ticket.get("visitor_type", "")))
            self.history_table.setItem(row, 4, QTableWidgetItem(ticket.get("phone", "")))
            self.history_table.setItem(row, 5, QTableWidgetItem(ticket.get("purpose", "")))
            self.history_table.setItem(
                row,
                6,
                QTableWidgetItem(ticket.get("status", "").capitalize()),
            )

            timestamp = (
                ticket.get("completed_at")
                or ticket.get("recalled_at")
                or ticket.get("called_at")
                or ticket.get("created_at")
            )
            if timestamp:
                try:
                    event_time = datetime.fromisoformat(timestamp)
                    self.history_table.setItem(row, 7, QTableWidgetItem(event_time.strftime("%Y-%m-%d")))
                    self.history_table.setItem(row, 8, QTableWidgetItem(event_time.strftime("%I:%M %p")))
                except Exception:
                    self.history_table.setItem(row, 7, QTableWidgetItem(str(timestamp)[:10]))
                    self.history_table.setItem(row, 8, QTableWidgetItem(""))
            else:
                self.history_table.setItem(row, 7, QTableWidgetItem(""))
                self.history_table.setItem(row, 8, QTableWidgetItem(""))


class SMSLogDialog(QDialog):
    """Modal dialog displaying SMS dispatch logs and simulation audit trail."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mock SMS Simulation Log (This Session)")
        self.setMinimumSize(960, 560)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(
            """
            SMSLogDialog {
                background: #eef3ef;
            }
            QFrame#card {
                background: #ffffff;
                border-radius: 20px;
                border: 1px solid #e3ebe3;
            }
            QLabel#dialogTitle {
                color: #18241b;
                font-size: 22px;
                font-weight: 800;
            }
            QLabel#dialogSubtitle {
                color: #55665a;
                font-size: 13px;
            }
            QTableWidget {
                background: #fdfdfd;
                border: 1px solid #e3ebe3;
                border-radius: 14px;
                gridline-color: #f0f0f0;
                font-size: 12px;
            }
            QHeaderView::section {
                background: #edf2ee;
                color: #33483a;
                font-weight: 700;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #d7e3d8;
            }
            QPushButton#primaryButton {
                background: #0a8c3c;
                color: white;
                border: none;
                border-radius: 14px;
                padding: 10px 20px;
                font-weight: 700;
            }
            QPushButton#secondaryButton {
                background: #edf2ee;
                color: #294032;
                border: none;
                border-radius: 14px;
                padding: 10px 20px;
                font-weight: 700;
            }
            QPushButton#dangerButton {
                background: #fbe9e7;
                color: #c0392b;
                border: none;
                border-radius: 14px;
                padding: 10px 20px;
                font-weight: 700;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(14)

        header_col = QVBoxLayout()
        header_col.setSpacing(4)
        title = QLabel("Mock SMS Simulation Log")
        title.setObjectName("dialogTitle")
        subtitle = QLabel(
            "Shows only messages simulated in Mock Mode during this session (in-memory, most recent 100). "
            "Live gateway dispatches are tracked per ticket in the database, not in this log."
        )
        subtitle.setObjectName("dialogSubtitle")
        header_col.addWidget(title)
        header_col.addWidget(subtitle)
        card_layout.addLayout(header_col)

        self.log_table = QTableWidget()
        self.log_table.setColumnCount(6)
        self.log_table.setHorizontalHeaderLabels(
            ["Timestamp", "Event", "Ticket #", "Recipient", "Status", "Dispatched Message Content"]
        )
        self.log_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        card_layout.addWidget(self.log_table)

        btn_row = QHBoxLayout()
        self.clear_btn = QPushButton("CLEAR LOGS")
        self.clear_btn.setObjectName("dangerButton")
        self.refresh_btn = QPushButton("REFRESH")
        self.refresh_btn.setObjectName("secondaryButton")
        self.close_btn = QPushButton("CLOSE")
        self.close_btn.setObjectName("primaryButton")

        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.refresh_btn)
        btn_row.addWidget(self.close_btn)
        card_layout.addLayout(btn_row)

        layout.addWidget(card)

        self.close_btn.clicked.connect(self.close)

    def populate_logs(self, logs: List[Dict[str, Any]]):
        """Populate the log table with records."""
        self.log_table.setRowCount(len(logs))
        for row, entry in enumerate(reversed(logs)):
            ts = entry.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts)
                formatted_ts = dt.strftime("%Y-%m-%d %I:%M:%S %p")
            except Exception:
                formatted_ts = str(ts)

            event = str(entry.get("event_type", "sms")).upper()
            t_num = f"#{entry.get('ticket_number'):04d}" if entry.get("ticket_number") else "N/A"
            phone = entry.get("phone", "")
            status = str(entry.get("status", "unknown")).upper()
            msg = entry.get("message", "")

            self.log_table.setItem(row, 0, QTableWidgetItem(formatted_ts))
            self.log_table.setItem(row, 1, QTableWidgetItem(event))
            self.log_table.setItem(row, 2, QTableWidgetItem(t_num))
            self.log_table.setItem(row, 3, QTableWidgetItem(phone))

            status_item = QTableWidgetItem(status)
            if "DELIVERED" in status or "SENT" in status or "SUCCESS" in status:
                status_item.setForeground(QColor("#0a8c3c"))
            elif "MOCK" in status:
                status_item.setForeground(QColor("#1565c0"))
            else:
                status_item.setForeground(QColor("#c0392b"))
            self.log_table.setItem(row, 4, status_item)

            self.log_table.setItem(row, 5, QTableWidgetItem(msg))


class TelegramLogDialog(QDialog):
    """Modal dialog displaying Telegram Bot dispatch logs and simulation audit trail."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mock Telegram Bot Simulation Log (This Session)")
        self.setMinimumSize(960, 560)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(
            """
            TelegramLogDialog {
                background: #eef3ef;
            }
            QFrame#card {
                background: #ffffff;
                border-radius: 20px;
                border: 1px solid #e3ebe3;
            }
            QLabel#dialogTitle {
                color: #18241b;
                font-size: 22px;
                font-weight: 800;
            }
            QLabel#dialogSubtitle {
                color: #55665a;
                font-size: 13px;
            }
            QTableWidget {
                background: #fdfdfd;
                border: 1px solid #e3ebe3;
                border-radius: 14px;
                gridline-color: #f0f0f0;
                font-size: 12px;
            }
            QHeaderView::section {
                background: #edf2ee;
                color: #33483a;
                font-weight: 700;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #d7e3d8;
            }
            QPushButton#primaryButton {
                background: #0088cc;
                color: white;
                border: none;
                border-radius: 14px;
                padding: 10px 20px;
                font-weight: 700;
            }
            QPushButton#secondaryButton {
                background: #edf2ee;
                color: #294032;
                border: none;
                border-radius: 14px;
                padding: 10px 20px;
                font-weight: 700;
            }
            QPushButton#dangerButton {
                background: #fbe9e7;
                color: #c0392b;
                border: none;
                border-radius: 14px;
                padding: 10px 20px;
                font-weight: 700;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(14)

        header_col = QVBoxLayout()
        header_col.setSpacing(4)
        title = QLabel("Mock Telegram Bot Simulation Log")
        title.setObjectName("dialogTitle")
        subtitle = QLabel(
            "Shows only Telegram messages simulated in Mock Mode during this session (in-memory, most recent 100). "
            "Live bot API dispatches are tracked per ticket in the database, not in this log."
        )
        subtitle.setObjectName("dialogSubtitle")
        header_col.addWidget(title)
        header_col.addWidget(subtitle)
        card_layout.addLayout(header_col)

        self.log_table = QTableWidget()
        self.log_table.setColumnCount(6)
        self.log_table.setHorizontalHeaderLabels(
            ["Timestamp", "Event", "Ticket #", "Chat ID / Recipient", "Status", "Dispatched Telegram Message Content"]
        )
        self.log_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        card_layout.addWidget(self.log_table)

        btn_row = QHBoxLayout()
        self.clear_btn = QPushButton("CLEAR LOGS")
        self.clear_btn.setObjectName("dangerButton")
        self.refresh_btn = QPushButton("REFRESH")
        self.refresh_btn.setObjectName("secondaryButton")
        self.close_btn = QPushButton("CLOSE")
        self.close_btn.setObjectName("primaryButton")

        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.refresh_btn)
        btn_row.addWidget(self.close_btn)
        card_layout.addLayout(btn_row)

        layout.addWidget(card)

        self.close_btn.clicked.connect(self.close)

    def populate_logs(self, logs: List[Dict[str, Any]]):
        """Populate the log table with records."""
        self.log_table.setRowCount(len(logs))
        for row, entry in enumerate(reversed(logs)):
            ts = entry.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts)
                formatted_ts = dt.strftime("%Y-%m-%d %I:%M:%S %p")
            except Exception:
                formatted_ts = str(ts)

            event = str(entry.get("event_type", "telegram")).upper()
            t_num = f"#{entry.get('ticket_number'):04d}" if entry.get("ticket_number") else "N/A"
            chat_id = str(entry.get("chat_id", ""))
            status = str(entry.get("status", "unknown")).upper()
            msg = entry.get("message", "")

            self.log_table.setItem(row, 0, QTableWidgetItem(formatted_ts))
            self.log_table.setItem(row, 1, QTableWidgetItem(event))
            self.log_table.setItem(row, 2, QTableWidgetItem(t_num))
            self.log_table.setItem(row, 3, QTableWidgetItem(chat_id))

            status_item = QTableWidgetItem(status)
            if "DELIVERED" in status or "SENT" in status or "SUCCESS" in status:
                status_item.setForeground(QColor("#0088cc"))
            elif "MOCK" in status:
                status_item.setForeground(QColor("#0a8c3c"))
            else:
                status_item.setForeground(QColor("#c0392b"))
            self.log_table.setItem(row, 4, status_item)

            self.log_table.setItem(row, 5, QTableWidgetItem(msg))

