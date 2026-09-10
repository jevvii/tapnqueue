"""
Student Kiosk Ticketing System - User Registration Station.
Single-page kiosk form styled for modern campus touchscreens.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from tapnque.config import get_asset_path
from tapnque.core.database import get_database
from tapnque.services.email_service import is_email_configured, send_ticket_email
from tapnque.services.sms_service import sanitize_ph_phone_number, send_ticket_created_sms
from tapnque.services.telegram_service import send_ticket_created_telegram
from tapnque.ui.components.animations import AnimatedLoadingBar, AnimatedSpinner
from tapnque.ui.components.dialogs import TicketCreatedDialog
from tapnque.ui.components.keyboard import TouchKeyboardWidget


class LoadingScreen(QWidget):
    """Fullscreen animated startup screen shown before the kiosk form."""

    def __init__(self, target_window):
        super().__init__()
        self.target_window = target_window
        self.logo_source = get_asset_path("OLFU LOGO 1.png")
        self.status_messages = [
            "INITIALIZING TERMINAL SESSION",
            "SYNCING CAMPUS SERVICES",
            "PREPARING CHECK-IN SCREEN",
        ]
        self.status_index = 0
        self._finished = False
        self._setup_ui()

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._advance_status)
        self.status_timer.start(900)

        self.finish_timer = QTimer(self)
        self.finish_timer.setSingleShot(True)
        self.finish_timer.timeout.connect(self._finish_loading)
        self.finish_timer.start(4000)

    def _setup_ui(self):
        self.setWindowTitle("TapNQue Loading")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet(
            """
            LoadingScreen {
                background: transparent;
            }
            QFrame#logoBadge {
                background: rgba(17, 33, 43, 0.78);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 34px;
            }
            QLabel#titleLabel {
                color: #f6f5ef;
                font-size: 68px;
                font-weight: 900;
                letter-spacing: 1px;
            }
            QLabel#subtitleLabel {
                color: #46a864;
                font-size: 24px;
                font-weight: 700;
                letter-spacing: 6px;
            }
            QLabel#loadingCopy {
                color: rgba(247, 244, 235, 0.92);
                font-size: 17px;
                font-weight: 500;
            }
            QLabel#statusLabel {
                color: rgba(215, 212, 203, 0.5);
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 3px;
            }
            QLabel#footerLabel {
                color: rgba(189, 192, 201, 0.4);
                font-size: 12px;
                font-weight: 700;
            }
            QLabel#lineLabel {
                color: rgba(189, 192, 201, 0.32);
                font-size: 16px;
                font-weight: 300;
            }
            """
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(64, 54, 64, 40)
        root_layout.setSpacing(0)
        root_layout.addStretch()

        center_layout = QVBoxLayout()
        center_layout.setSpacing(18)
        center_layout.setAlignment(Qt.AlignHCenter)

        badge = QFrame()
        badge.setObjectName("logoBadge")
        badge.setFixedSize(206, 206)
        badge_layout = QVBoxLayout(badge)
        badge_layout.setContentsMargins(24, 24, 24, 24)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(str(self.logo_source))
        if not pixmap.isNull():
            scaled = pixmap.scaled(126, 126, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled)
        else:
            logo_label.setText("OLFU")
            logo_label.setStyleSheet("color: #0b9b4a; font-size: 38px; font-weight: 800;")
        badge_layout.addWidget(logo_label, 1, Qt.AlignCenter)

        center_layout.addWidget(badge, 0, Qt.AlignCenter)

        title = QLabel("TapNQue")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(title)

        subtitle = QLabel("KIOSK TERMINAL")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(subtitle)

        center_layout.addSpacing(56)

        spinner = AnimatedSpinner()
        center_layout.addWidget(spinner, 0, Qt.AlignCenter)

        loading_copy = QLabel("Please wait while loading....")
        loading_copy.setObjectName("loadingCopy")
        loading_copy.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(loading_copy)

        center_layout.addSpacing(10)

        status_row = QHBoxLayout()
        status_row.setSpacing(14)
        left_line = QLabel("────")
        left_line.setObjectName("lineLabel")
        right_line = QLabel("────")
        right_line.setObjectName("lineLabel")
        self.status_label = QLabel(self.status_messages[self.status_index])
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_row.addStretch()
        status_row.addWidget(left_line)
        status_row.addWidget(self.status_label)
        status_row.addWidget(right_line)
        status_row.addStretch()
        center_layout.addLayout(status_row)

        root_layout.addLayout(center_layout)
        root_layout.addStretch()

        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(12)

        footer_bar = AnimatedLoadingBar()
        footer_layout.addWidget(footer_bar, 0, Qt.AlignHCenter)

        footer_labels = QHBoxLayout()
        footer_labels.setContentsMargins(0, 0, 0, 0)
        footer_labels.setSpacing(24)

        terminal_label = QLabel("TERMINAL: K-01249")
        terminal_label.setObjectName("footerLabel")
        version_label = QLabel("VERSION: 2.0.0-PROD")
        version_label.setObjectName("footerLabel")
        security_label = QLabel("STATUS: READY")
        security_label.setObjectName("footerLabel")

        footer_labels.addWidget(terminal_label)
        footer_labels.addStretch()
        footer_labels.addWidget(version_label)
        footer_labels.addStretch()
        footer_labels.addWidget(security_label)
        footer_layout.addLayout(footer_labels)

        root_layout.addLayout(footer_layout)

    def _advance_status(self):
        self.status_index = (self.status_index + 1) % len(self.status_messages)
        self.status_label.setText(self.status_messages[self.status_index])

    def _finish_loading(self):
        if self._finished:
            return
        self._finished = True
        self.status_timer.stop()
        self.target_window.showFullScreen()
        self.close()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Escape, Qt.Key_Return, Qt.Key_Space):
            self._finish_loading()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor("#04151d"))
        gradient.setColorAt(0.55, QColor("#03101a"))
        gradient.setColorAt(1.0, QColor("#070913"))
        painter.fillRect(self.rect(), gradient)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(9, 38, 33, 42))
        painter.drawEllipse(int(self.width() * 0.22), int(self.height() * 0.12), 520, 520)

        painter.setBrush(QColor(16, 20, 44, 30))
        painter.drawEllipse(int(self.width() * 0.56), int(self.height() * 0.42), 620, 620)


class StudentKiosk(QWidget):
    """Main student kiosk registration window."""

    def __init__(self):
        super().__init__()
        self.db = get_database()
        self.background_source = get_asset_path("Background Olfu bw.jpg")
        self.background_pixmap = QPixmap(str(self.background_source))
        self.logo_1_source = get_asset_path("OLFU LOGO 1.jpg")
        self.logo_2_source = get_asset_path("OLFU LOGO 2.png")
        self.phone_number_enabled = self.db.get_app_settings().get("phone_number_enabled", True)
        self._setup_ui()
        self.settings_timer = QTimer(self)
        self.settings_timer.timeout.connect(self._refresh_phone_field_setting)
        self.settings_timer.start(5000)

    def _setup_ui(self):
        self.setWindowTitle("Student Kiosk - Get Your Ticket")
        self.setMinimumSize(1280, 820)
        self.setStyleSheet(
            """
            StudentKiosk {
                background: #dfe6df;
            }
            QFrame#pageOverlay {
                background: rgba(245, 248, 245, 176);
            }
            QLabel, QPushButton, QLineEdit, QComboBox {
                color: #203126;
                font-family: "Segoe UI";
            }
            QFrame#topBar {
                background: rgba(247, 250, 247, 232);
                border: none;
                border-radius: 0px;
            }
            QFrame#sidePanel {
                background: transparent;
            }
            QLabel#brandLogo {
                color: #0b9b4a;
                font-size: 30px;
                font-weight: 800;
            }
            QLabel#brandName {
                color: #0b9b4a;
                font-size: 27px;
                font-weight: 800;
            }
            QLabel#headerLogo {
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
            QPushButton#sideButton:hover {
                background: rgba(255, 255, 255, 0.62);
            }
            QPushButton#sideButton[active="true"] {
                background: rgba(255, 255, 255, 0.96);
                color: #0b9b4a;
            }
            QFrame#card {
                background: rgba(255, 255, 255, 0.96);
                border-radius: 34px;
                border: 1px solid #e3ebe3;
            }
            QLabel#cardTitle {
                color: #18241b;
                font-size: 42px;
                font-weight: 800;
            }
            QLabel#cardSubtitle {
                color: #55665a;
                font-size: 17px;
            }
            QLabel#fieldLabel {
                color: #33483a;
                font-size: 14px;
                font-weight: 700;
            }
            QLineEdit, QComboBox {
                background: rgba(237, 242, 238, 0.96);
                color: #172019;
                border: 2px solid #edf2ee;
                border-radius: 16px;
                padding: 16px 18px;
                font-size: 14px;
                min-height: 34px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #0b9b4a;
                background: #f7fbf8;
            }
            QLineEdit::placeholder {
                color: #9daea0;
            }
            QComboBox {
                padding-right: 32px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background: #f7fbf8;
                color: #203126;
                border: 1px solid #d7e3d8;
                selection-background-color: #0b9b4a;
                selection-color: #ffffff;
                outline: 0;
                padding: 6px;
            }
            QPushButton#submitButton {
                background: #0a8c3c;
                color: white;
                border: none;
                border-radius: 18px;
                padding: 22px;
                font-size: 22px;
                font-weight: 800;
            }
            QPushButton#submitButton:hover {
                background: #087632;
            }
            QPushButton#submitButton:pressed {
                background: #066229;
            }
            QFrame#infoBox {
                background: rgba(242, 247, 242, 0.96);
                border-left: 4px solid #0b9b4a;
                border-radius: 18px;
            }
            QLabel#infoIcon {
                color: #0b9b4a;
                font-size: 22px;
                font-weight: 800;
            }
            QLabel#infoText {
                color: #304336;
                font-size: 15px;
            }
            QFrame#touchKeyboard {
                background: rgba(36, 46, 61, 0.98);
                border: 1px solid rgba(88, 104, 128, 0.75);
                border-radius: 28px;
            }
            QPushButton#keyboardKey,
            QPushButton#keyboardDeleteKey,
            QPushButton#keyboardEnterKey,
            QPushButton#keyboardCloseKey {
                background: #475368;
                color: #f2f5f8;
                border: none;
                border-radius: 14px;
                font-size: 20px;
                font-weight: 700;
                padding: 12px 14px;
            }
            QPushButton#keyboardKey:hover,
            QPushButton#keyboardDeleteKey:hover {
                background: #56647c;
            }
            QPushButton#keyboardDeleteKey {
                background: #c62828;
            }
            QPushButton#keyboardDeleteKey:hover {
                background: #b71c1c;
            }
            QPushButton#keyboardEnterKey {
                background: #0a8c3c;
            }
            QPushButton#keyboardEnterKey:hover {
                background: #087632;
            }
            QPushButton#keyboardCloseKey {
                background: #2d3748;
                font-size: 16px;
                padding: 10px 14px;
            }
            QPushButton#keyboardCloseKey:hover {
                background: #3a4659;
            }
            """
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        page_overlay = QFrame()
        page_overlay.setObjectName("pageOverlay")
        overlay_layout = QVBoxLayout(page_overlay)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setSpacing(0)
        root_layout.addWidget(page_overlay)

        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(86)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(42, 18, 42, 18)
        top_layout.setSpacing(10)

        logo_1 = self._create_logo_label(self.logo_1_source, 42)
        top_layout.addWidget(logo_1)

        logo_2 = self._create_logo_label(self.logo_2_source, 42)
        top_layout.addWidget(logo_2)

        brand_name = QLabel("TapNQue")
        brand_name.setObjectName("brandName")
        top_layout.addWidget(brand_name)
        top_layout.addStretch()

        overlay_layout.addWidget(top_bar)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(28, 18, 32, 32)
        body_layout.setSpacing(30)
        overlay_layout.addWidget(body)

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

        side_terminal = QLabel("Kiosk Terminal 01")
        side_terminal.setObjectName("terminalName")
        side_layout.addWidget(side_terminal)

        side_layout.addSpacing(28)

        checkin_button = QPushButton("->  Check In")
        checkin_button.setObjectName("sideButton")
        checkin_button.setProperty("active", True)
        checkin_button.setCursor(Qt.PointingHandCursor)
        side_layout.addWidget(checkin_button)
        side_layout.addStretch()

        body_layout.addWidget(side_panel, 0, Qt.AlignTop)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(76, 56, 76, 48)
        card_layout.setSpacing(26)

        title = QLabel("Queue Registration")
        title.setObjectName("cardTitle")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("Please provide your details to receive your service ticket.")
        subtitle.setObjectName("cardSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(12)

        form_grid = QGridLayout()
        form_grid.setHorizontalSpacing(36)
        form_grid.setVerticalSpacing(18)

        name_label = QLabel("STUDENT NAME")
        name_label.setObjectName("fieldLabel")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("ex Juan Dela Cruz")

        id_label = QLabel("STUDENT NUMBER")
        id_label.setObjectName("fieldLabel")
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("2023-00000")
        self.id_input.setProperty("numeric_format", "student_id")

        email_label = QLabel("EMAIL ADDRESS")
        email_label.setObjectName("fieldLabel")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("student@domain.edu")

        self.phone_label = QLabel("PHONE NUMBER")
        self.phone_label.setObjectName("fieldLabel")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("09XX XXX XXXX")

        visitor_label = QLabel("VISITOR TYPE")
        visitor_label.setObjectName("fieldLabel")
        self.visitor_combo = QComboBox()
        self.visitor_combo.addItems(["Student", "Parent", "Guardian", "PWD"])

        telegram_label = QLabel("TELEGRAM USERNAME / CHAT ID (OPTIONAL)")
        telegram_label.setObjectName("fieldLabel")
        self.telegram_input = QLineEdit()
        self.telegram_input.setPlaceholderText("e.g. @username or Chat ID")

        purpose_label = QLabel("PURPOSE OF VISIT")
        purpose_label.setObjectName("fieldLabel")
        self.purpose_combo = QComboBox()
        self.purpose_combo.addItems(
            [
                "Select an option",
                "Enrollment",
                "Student Permit",
                "Grades",
                "Clearance",
                "Special Exam",
                "Others",
            ]
        )

        form_grid.addWidget(name_label, 0, 0)
        form_grid.addWidget(id_label, 0, 1)
        form_grid.addWidget(self.name_input, 1, 0)
        form_grid.addWidget(self.id_input, 1, 1)
        form_grid.addWidget(email_label, 2, 0)
        form_grid.addWidget(self.phone_label, 2, 1)
        form_grid.addWidget(self.email_input, 3, 0)
        form_grid.addWidget(self.phone_input, 3, 1)
        form_grid.addWidget(visitor_label, 4, 0)
        form_grid.addWidget(telegram_label, 4, 1)
        form_grid.addWidget(self.visitor_combo, 5, 0)
        form_grid.addWidget(self.telegram_input, 5, 1)
        form_grid.addWidget(purpose_label, 6, 0, 1, 2)
        form_grid.addWidget(self.purpose_combo, 7, 0, 1, 2)
        self._apply_phone_field_visibility()

        card_layout.addLayout(form_grid)
        card_layout.addSpacing(22)

        self.submit_btn = QPushButton("GET TICKET")
        self.submit_btn.setObjectName("submitButton")
        self.submit_btn.setCursor(Qt.PointingHandCursor)
        self.submit_btn.clicked.connect(self._submit_ticket)
        card_layout.addWidget(self.submit_btn)

        info_box = QFrame()
        info_box.setObjectName("infoBox")
        info_layout = QHBoxLayout(info_box)
        info_layout.setContentsMargins(26, 24, 26, 24)
        info_layout.setSpacing(16)

        info_icon = QLabel("i")
        info_icon.setObjectName("infoIcon")
        info_icon.setAlignment(Qt.AlignCenter)
        info_icon.setFixedWidth(22)
        info_layout.addWidget(info_icon, 0, Qt.AlignTop)

        info_text = QLabel("Your digital ticket will be displayed immediately upon submission.")
        info_text.setObjectName("infoText")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)

        card_layout.addWidget(info_box)
        body_layout.addWidget(card, 1)

        self.keyboard = TouchKeyboardWidget(self)

        for field, keyboard_type in (
            (self.name_input, "alpha"),
            (self.id_input, "numeric"),
            (self.email_input, "alpha"),
            (self.phone_input, "numeric"),
            (self.telegram_input, "alpha"),
        ):
            field.setProperty("keyboard_type", keyboard_type)
            field.installEventFilter(self)

        self._apply_fonts()
        self._position_keyboard()

    def _apply_fonts(self):
        self.setFont(QFont("Segoe UI", 11))

    def _create_logo_label(self, image_path: Path, height: int) -> QLabel:
        label = QLabel()
        label.setObjectName("headerLogo")
        label.setFixedHeight(height)
        label.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap(str(image_path))
        if not pixmap.isNull():
            scaled = pixmap.scaledToHeight(height, Qt.SmoothTransformation)
            label.setPixmap(scaled)
            label.setFixedWidth(scaled.width())
        else:
            label.setFixedWidth(height)

        return label

    def eventFilter(self, watched, event):
        if event.type() == QEvent.FocusIn and isinstance(watched, QLineEdit):
            keyboard_type = watched.property("keyboard_type") or "alpha"
            self.keyboard.attach_target(watched, keyboard_type)
            self._position_keyboard()
        return super().eventFilter(watched, event)

    def _position_keyboard(self):
        keyboard_width = min(860, max(520, self.width() - 120))
        if self.keyboard.width() != keyboard_width:
            self.keyboard.setFixedWidth(keyboard_width)

        x = (self.width() - self.keyboard.width()) // 2
        y = self.height() - self.keyboard.height() - 18
        self.keyboard.move(max(20, x), max(100, y))

    def _apply_phone_field_visibility(self):
        self.phone_label.setVisible(self.phone_number_enabled)
        self.phone_input.setVisible(self.phone_number_enabled)
        if not self.phone_number_enabled:
            self.phone_input.clear()
            if hasattr(self, "keyboard") and self.keyboard.target_input is self.phone_input:
                self.keyboard.hide()

    def _refresh_phone_field_setting(self):
        enabled = self.db.get_cached_app_settings().get("phone_number_enabled", True)
        if enabled == self.phone_number_enabled:
            return

        self.phone_number_enabled = enabled
        self._apply_phone_field_visibility()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_keyboard()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.isFullScreen():
            self.showNormal()
            return
        if event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        if not self.background_pixmap.isNull():
            scaled = self.background_pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

        painter.fillRect(self.rect(), Qt.transparent)
        super().paintEvent(event)

    def _submit_ticket(self):
        name = self.name_input.text().strip()
        student_id = self.id_input.text().strip()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip() if self.phone_number_enabled else ""
        visitor_type = self.visitor_combo.currentText()
        purpose = self.purpose_combo.currentText()

        if not name or not student_id:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please enter your student name and student number.",
            )
            return

        if purpose == "Select an option":
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please select your purpose of visit.",
            )
            return

        phone_formatted = ""
        if self.phone_number_enabled and phone:
            phone_formatted = sanitize_ph_phone_number(phone)
            if not phone_formatted:
                QMessageBox.warning(
                    self,
                    "Invalid Phone Number",
                    "Please enter a valid 11-digit Philippine mobile number\n(e.g., 0917 123 4567 or +639171234567).",
                )
                return

        telegram_chat = self.telegram_input.text().strip()

        try:
            ticket = self.db.create_ticket(
                name=name,
                student_id=student_id,
                email=email,
                phone=phone,
                purpose=purpose,
                visitor_type=visitor_type,
                phone_formatted=phone_formatted,
                telegram_chat_id=telegram_chat,
            )
            queue_position = 1
            waiting_queue = self.db.get_waiting_queue()
            for index, queued_ticket in enumerate(waiting_queue, start=1):
                if queued_ticket.get("ticket_number") == ticket["ticket_number"]:
                    queue_position = index
                    break

            if email and is_email_configured():
                send_ticket_email(
                    to_email=email,
                    student_name=name,
                    ticket_number=ticket["ticket_number"],
                    position=queue_position,
                    reason=purpose,
                    async_send=True,
                )
                email_sent = True
            else:
                email_sent = False

            sms_sent = False
            if phone_formatted:
                sms_sent = send_ticket_created_sms(ticket, queue_position)

            telegram_sent = False
            if telegram_chat:
                telegram_sent = send_ticket_created_telegram(ticket, queue_position)

            self.keyboard.hide()
            confirmation = TicketCreatedDialog(
                ticket=ticket,
                queue_position=queue_position,
                purpose=purpose,
                email_sent=email_sent,
                sms_sent=sms_sent,
                telegram_sent=telegram_sent,
                parent=self,
            )
            confirmation.resize(960, 660)
            confirmation.exec()
            self._clear_form()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create ticket: {str(e)}")

    def _clear_form(self):
        self.name_input.clear()
        self.id_input.clear()
        self.email_input.clear()
        self.phone_input.clear()
        self.telegram_input.clear()
        self.visitor_combo.setCurrentIndex(0)
        self.purpose_combo.setCurrentIndex(0)
        self.keyboard.hide()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = StudentKiosk()
    loading = LoadingScreen(window)
    loading.showFullScreen()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
