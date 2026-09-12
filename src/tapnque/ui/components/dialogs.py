import logging
from datetime import datetime
from typing import List, Dict, Any

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QGuiApplication,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)
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
    QWidget,
)

from tapnque.config import get_asset_path
from tapnque.core.database import get_database
from tapnque.services.telegram_service import generate_telegram_qr_pixmap
from tapnque.ui.components.animations import WaitingSignalAnimation

logger = logging.getLogger("tapnque.dialogs")


class GeometricCornerWidget(QWidget):
    """Draws modern geometric school-colored angular shapes in the top-right corner."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 70)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        w, h = self.width(), self.height()

        # Triangle 1: Fatima Warm Gold (#f59e0b)
        poly1 = QPolygonF([QPointF(w - 75, 0), QPointF(w, 0), QPointF(w, 50)])
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#f59e0b"))
        painter.drawPolygon(poly1)

        # Triangle 2: Vibrant Fatima Emerald (#10b981)
        poly2 = QPolygonF([QPointF(w - 110, 0), QPointF(w - 50, 0), QPointF(w - 80, 28)])
        painter.setBrush(QColor("#10b981"))
        painter.drawPolygon(poly2)

        # Triangle 3: Telegram Blue accent (#0284c7)
        poly3 = QPolygonF([QPointF(w - 48, 16), QPointF(w - 12, 50), QPointF(w - 48, 50)])
        painter.setBrush(QColor("#0284c7"))
        painter.drawPolygon(poly3)

        # Triangle 4: Bright Yellow highlight (#fbbf24)
        poly4 = QPolygonF([QPointF(w - 22, 48), QPointF(w, 48), QPointF(w - 10, 64)])
        painter.setBrush(QColor("#fbbf24"))
        painter.drawPolygon(poly4)


class NotchedBannerWidget(QFrame):
    """Boarding-pass middle transition banner with side cutouts and transit indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(66)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()
        r = 13  # cutout notch radius

        # Banner body (Deep Fatima Green gradient)
        gradient = QLinearGradient(0, 0, w, 0)
        gradient.setColorAt(0.0, QColor("#083520"))
        gradient.setColorAt(0.5, QColor("#0e5232"))
        gradient.setColorAt(1.0, QColor("#083520"))

        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, 14, 14)

        # Left notch cutout
        left_notch = QPainterPath()
        left_notch.addEllipse(QRectF(-r, (h / 2) - r, r * 2, r * 2))
        path = path.subtracted(left_notch)

        # Right notch cutout
        right_notch = QPainterPath()
        right_notch.addEllipse(QRectF(w - r, (h / 2) - r, r * 2, r * 2))
        path = path.subtracted(right_notch)

        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawPath(path)

        # Dashed perforation lines near bottom of banner
        pen = QPen(QColor(255, 255, 255, 70), 1.5, Qt.DashLine)
        pen.setDashPattern([3, 4])
        painter.setPen(pen)
        painter.drawLine(r + 8, h - 2, w - r - 8, h - 2)


class TicketCreatedDialog(QDialog):
    """Modern boarding-pass style queue ticket modal.

    Features:
    - Airline/event boarding pass layout with clean top QR placement.
    - Notched transit banner with transit arrow/plane.
    - Lower ticket stub containing visitor credentials, service, and queue metrics.
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
            if self.telegram_offered:
                self.auto_close_hint.setText(
                    f"⏱ Auto-closing in {self.remaining_seconds}s • Take photo or scan QR"
                )
            else:
                self.auto_close_hint.setText(
                    f"⏱ Auto-closing in {self.remaining_seconds}s • Please remember ticket"
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
                    self.scan_status_pill.setText("✅ Telegram Connected! Auto-closing...")
                    self.scan_status_pill.setStyleSheet(
                        "background: #065f46; color: #ffffff; border: 1px solid #34d399; "
                        "border-radius: 12px; padding: 6px 14px; font-size: 11px; font-weight: 800;"
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
        self.setWindowTitle("Queue Boarding Pass")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setStyleSheet(
            """
            TicketCreatedDialog {
                background: transparent;
                font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Noto Sans", sans-serif;
            }
            QFrame#cardBackground {
                background: #ffffff;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 26px;
            }
            QLabel#orgHeader {
                color: #083822;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 1.5px;
            }
            QLabel#passType {
                color: #64748b;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#tgReqBadge {
                background: rgba(34, 158, 217, 0.12);
                color: #0284c7;
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 10px;
                padding: 4px 12px;
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 1.2px;
            }
            QLabel#scanHint {
                color: #475569;
                font-size: 11px;
                font-weight: 600;
            }
            QLabel#ticketNoText {
                color: #0f172a;
                font-size: 13px;
                font-weight: 800;
                letter-spacing: 1.5px;
            }
            QLabel#transitLabel {
                color: rgba(255, 255, 255, 0.7);
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1.5px;
            }
            QLabel#transitValue {
                color: #fbbf24;
                font-size: 17px;
                font-weight: 900;
            }
            QLabel#transitSub {
                color: rgba(255, 255, 255, 0.85);
                font-size: 10px;
                font-weight: 600;
            }
            QLabel#transitArrow {
                color: #fbbf24;
                font-size: 14px;
                font-weight: 900;
            }
            QFrame#bottomStub {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 18px;
            }
            QLabel#stubFieldLabel {
                color: #64748b;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QLabel#stubFieldValue {
                color: #0f172a;
                font-size: 13px;
                font-weight: 800;
            }
            QLabel#stubNameValue {
                color: #083822;
                font-size: 17px;
                font-weight: 900;
            }
            QLabel#scanStatusPill {
                background: rgba(16, 185, 129, 0.14);
                color: #047857;
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 12px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 800;
            }
            QPushButton#doneButton {
                background: #10b981;
                color: #032114;
                border: none;
                border-radius: 14px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 900;
            }
            QPushButton#doneButton:hover {
                background: #34d399;
            }
            """
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)

        card = QFrame()
        card.setObjectName("cardBackground")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(9)

        # 1. TOP HEADER
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        logo_label = QLabel()
        logo_pixmap = QPixmap(str(self.logo_source))
        if not logo_pixmap.isNull():
            logo_label.setPixmap(
                logo_pixmap.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        logo_label.setFixedSize(38, 38)
        logo_label.setAlignment(Qt.AlignCenter)
        header_row.addWidget(logo_label, 0, Qt.AlignVCenter)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(1)
        org_title = QLabel("OUR LADY OF FATIMA UNIVERSITY")
        org_title.setObjectName("orgHeader")
        brand_col.addWidget(org_title)

        pass_type = QLabel("STUDENT QUEUE PASS • CONFIRMED")
        pass_type.setObjectName("passType")
        brand_col.addWidget(pass_type)
        header_row.addLayout(brand_col, 1)

        corner_widget = GeometricCornerWidget()
        header_row.addWidget(corner_widget, 0, Qt.AlignRight | Qt.AlignTop)
        card_layout.addLayout(header_row)

        # 2. HERO QR CODE SECTION
        qr_col = QVBoxLayout()
        qr_col.setSpacing(5)
        qr_col.setAlignment(Qt.AlignCenter)

        if self.telegram_offered:
            tg_badge = QLabel("✈️ TELEGRAM QUEUE ALERTS REQUIRED")
            tg_badge.setObjectName("tgReqBadge")
            tg_badge.setAlignment(Qt.AlignCenter)
            qr_col.addWidget(tg_badge, 0, Qt.AlignCenter)

            scan_hint = QLabel("Point phone camera at QR code  •  Tap 'Start' in Telegram")
            scan_hint.setObjectName("scanHint")
            scan_hint.setAlignment(Qt.AlignCenter)
            qr_col.addWidget(scan_hint, 0, Qt.AlignCenter)
        else:
            std_badge = QLabel("DIGITAL QUEUE TICKET")
            std_badge.setObjectName("tgReqBadge")
            std_badge.setAlignment(Qt.AlignCenter)
            qr_col.addWidget(std_badge, 0, Qt.AlignCenter)

            scan_hint = QLabel("Please proceed to the waiting area and watch the monitor.")
            scan_hint.setObjectName("scanHint")
            scan_hint.setAlignment(Qt.AlignCenter)
            qr_col.addWidget(scan_hint, 0, Qt.AlignCenter)

        qr_pixmap = generate_telegram_qr_pixmap(self.ticket["ticket_number"], size=165)
        self.qr_label = QLabel()
        if qr_pixmap is not None:
            self.qr_label.setPixmap(qr_pixmap)
        self.qr_label.setFixedSize(165, 165)
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setCursor(Qt.PointingHandCursor)

        # Allow clicking QR to simulate scan during defense demo or testing
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

        self.qr_label.mousePressEvent = _on_qr_click
        qr_col.addWidget(self.qr_label, 0, Qt.AlignCenter)
        qr_col.addSpacing(6)

        flight_text = f"Ticket No : #{self.ticket['ticket_number']:04d}   •   Queue Pos : {self.queue_position}"
        ticket_no_label = QLabel(flight_text)
        ticket_no_label.setObjectName("ticketNoText")
        ticket_no_label.setAlignment(Qt.AlignCenter)
        qr_col.addWidget(ticket_no_label, 0, Qt.AlignCenter)

        card_layout.addLayout(qr_col)

        # 3. MIDDLE NOTCH TRANSITION BANNER
        banner = NotchedBannerWidget()
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(22, 4, 22, 4)

        from_col = QVBoxLayout()
        from_col.setSpacing(1)
        from_col.setAlignment(Qt.AlignCenter)
        from_lbl = QLabel("FROM")
        from_lbl.setObjectName("transitLabel")
        from_val = QLabel(f"POS {self.queue_position}")
        from_val.setObjectName("transitValue")
        from_sub = QLabel("Waiting Area")
        from_sub.setObjectName("transitSub")
        from_col.addWidget(from_lbl)
        from_col.addWidget(from_val)
        from_col.addWidget(from_sub)
        banner_layout.addLayout(from_col)

        center_plane_col = QVBoxLayout()
        center_plane_col.setSpacing(1)
        center_plane_col.setAlignment(Qt.AlignCenter)
        plane_symbol = "• - - - ✈ - - - •" if self.telegram_offered else "• - - - ➔ - - - •"
        plane_lbl = QLabel(plane_symbol)
        plane_lbl.setObjectName("transitArrow")
        plane_lbl.setAlignment(Qt.AlignCenter)
        center_sub = QLabel("Telegram Alerts" if self.telegram_offered else "Queue Transit")
        center_sub.setObjectName("transitSub")
        center_sub.setAlignment(Qt.AlignCenter)
        center_plane_col.addWidget(plane_lbl)
        center_plane_col.addWidget(center_sub)
        banner_layout.addLayout(center_plane_col)

        to_col = QVBoxLayout()
        to_col.setSpacing(1)
        to_col.setAlignment(Qt.AlignCenter)
        to_lbl = QLabel("TO")
        to_lbl.setObjectName("transitLabel")
        to_val = QLabel("COUNTER")
        to_val.setObjectName("transitValue")
        to_sub = QLabel("Lobby Display")
        to_sub.setObjectName("transitSub")
        to_col.addWidget(to_lbl)
        to_col.addWidget(to_val)
        to_col.addWidget(to_sub)
        banner_layout.addLayout(to_col)

        card_layout.addWidget(banner)

        # 4. LOWER TICKET STUB
        stub = QFrame()
        stub.setObjectName("bottomStub")
        stub_layout = QVBoxLayout(stub)
        stub_layout.setContentsMargins(16, 12, 16, 12)
        stub_layout.setSpacing(8)

        name_col = QVBoxLayout()
        name_col.setSpacing(1)
        name_lbl = QLabel("STUDENT / VISITOR NAME")
        name_lbl.setObjectName("stubFieldLabel")
        name_val = QLabel(self.ticket.get("full_name") or "Student Visitor")
        name_val.setObjectName("stubNameValue")
        name_col.addWidget(name_lbl)
        name_col.addWidget(name_val)
        stub_layout.addLayout(name_col)

        info_row1 = QHBoxLayout()
        col_svc = QVBoxLayout()
        col_svc.setSpacing(1)
        svc_lbl = QLabel("SERVICE / PURPOSE")
        svc_lbl.setObjectName("stubFieldLabel")
        svc_val = QLabel(self.purpose)
        svc_val.setObjectName("stubFieldValue")
        svc_val.setWordWrap(True)
        col_svc.addWidget(svc_lbl)
        col_svc.addWidget(svc_val)
        info_row1.addLayout(col_svc, 3)

        col_type = QVBoxLayout()
        col_type.setSpacing(1)
        type_lbl = QLabel("VISITOR TYPE")
        type_lbl.setObjectName("stubFieldLabel")
        type_val = QLabel(self.ticket.get("visitor_type", "Student"))
        type_val.setObjectName("stubFieldValue")
        col_type.addWidget(type_lbl)
        col_type.addWidget(type_val)
        info_row1.addLayout(col_type, 2)
        stub_layout.addLayout(info_row1)

        info_row2 = QHBoxLayout()
        col_time = QVBoxLayout()
        col_time.setSpacing(1)
        time_lbl = QLabel("ISSUED TIME")
        time_lbl.setObjectName("stubFieldLabel")
        now_str = datetime.now().strftime("%H:%M  %d-%b-%Y")
        time_val = QLabel(now_str)
        time_val.setObjectName("stubFieldValue")
        col_time.addWidget(time_lbl)
        col_time.addWidget(time_val)
        info_row2.addLayout(col_time, 3)

        col_chan = QVBoxLayout()
        col_chan.setSpacing(1)
        chan_lbl = QLabel("STATUS / ALERTS")
        chan_lbl.setObjectName("stubFieldLabel")
        notes = []
        if self.email_sent:
            notes.append("Email ✓")
        if self.telegram_offered:
            notes.append("Telegram Bot")
        chan_val = QLabel(" • ".join(notes) if notes else "Lobby Monitor")
        chan_val.setObjectName("stubFieldValue")
        col_chan.addWidget(chan_lbl)
        col_chan.addWidget(chan_val)
        info_row2.addLayout(col_chan, 2)
        stub_layout.addLayout(info_row2)

        card_layout.addWidget(stub)

        # 5. SCANNER PILL
        if self.telegram_offered:
            self.scan_status_pill = QLabel("🟢 Scanner active • Waiting for Telegram scan...")
        else:
            self.scan_status_pill = QLabel("🟢 Ticket Active • Please watch the lobby screen")
        self.scan_status_pill.setObjectName("scanStatusPill")
        self.scan_status_pill.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.scan_status_pill, 0, Qt.AlignCenter)

        # 6. FOOTER
        footer_row = QHBoxLayout()
        footer_row.setSpacing(10)

        if self.telegram_offered:
            hint_text = "⏱ Auto-closing in 30s • Take photo or scan QR"
        else:
            hint_text = "⏱ Auto-closing in 30s • Please remember ticket"
        self.auto_close_hint = QLabel(hint_text)
        self.auto_close_hint.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")
        footer_row.addWidget(self.auto_close_hint, 1)

        self.done_button = QPushButton("DONE (30s)")
        self.done_button.setObjectName("doneButton")
        self.done_button.setCursor(Qt.PointingHandCursor)
        self.done_button.clicked.connect(self.accept)
        footer_row.addWidget(self.done_button)
        card_layout.addLayout(footer_row)

        root_layout.addWidget(card)

    def _finalize_sizing(self):
        """Size the dialog to the boarding-pass dimensions clamped to screen."""
        self.adjustSize()
        width = 470
        height = 680
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            width = min(width, int(available.width() * 0.94))
            height = min(height, int(available.height() * 0.94))
        self.resize(width, height)
        self.setFixedSize(width, height)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(4, 12, 8, 175))


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

