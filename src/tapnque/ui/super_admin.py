"""
Super Admin UI - Executive Analytics and Queue Administration Station.
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tapnque.core.auth import require_admin_login
from tapnque.core.database import get_database
from tapnque.services.telegram_service import (
    clear_mock_telegram_history,
    ensure_link_listener,
    fetch_recent_telegram_users,
    format_telegram_template,
    generate_telegram_qr_pixmap,
    get_mock_telegram_history,
    get_telegram_bot_link,
    resolve_telegram_chat_id,
    send_via_telegram_api,
    simulate_mock_telegram,
    validate_telegram_bot_token,
)
from tapnque.ui.components.dialogs import TelegramLogDialog


class StatCard(QFrame):
    """Compact metric card styled to match the admin surfaces."""

    def __init__(self, title: str, value: Any, accent: str, helper_text: str = "", parent=None):
        super().__init__(parent)
        self._setup_ui(title, value, accent, helper_text)

    def _setup_ui(self, title: str, value: Any, accent: str, helper_text: str):
        self.setObjectName("statCard")
        self.setMinimumHeight(170)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("statLabel")
        layout.addWidget(title_label)

        self.value_label = QLabel(str(value))
        self.value_label.setObjectName("statValue")
        self.value_label.setStyleSheet(f"color: {accent};")
        layout.addWidget(self.value_label)

        self.helper_label = QLabel(helper_text)
        self.helper_label.setObjectName("statHelper")
        self.helper_label.setWordWrap(True)
        self.helper_label.setMinimumHeight(34)
        layout.addWidget(self.helper_label)

    def update_value(self, value: Any):
        self.value_label.setText(str(value))

    def update_helper(self, text: str):
        self.helper_label.setText(text)


class SuperAdmin(QWidget):
    """Super admin analytics and operations dashboard."""

    def __init__(self):
        super().__init__()
        self.authenticated = require_admin_login("super_admin", "Super Admin Login", self)
        if not self.authenticated:
            return

        self.db = get_database()
        self._setup_ui()
        self._update_phone_toggle_ui()
        self._update_telegram_ui()
        self._setup_timer()

    def _setup_ui(self):
        self.setWindowTitle("Super Admin - Analytics Dashboard")
        self.setMinimumSize(1360, 860)
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
            QTabWidget::pane {
                border: none;
                background: transparent;
                margin-top: 18px;
            }
            QTabBar::tab {
                background: #edf2ee;
                color: #516257;
                border: none;
                border-radius: 16px;
                padding: 14px 18px;
                margin-right: 10px;
                font-size: 14px;
                font-weight: 700;
            }
            QTabBar::tab:selected {
                background: #0a8c3c;
                color: #ffffff;
            }
            QFrame#sectionPanel, QGroupBox#sectionPanel {
                background: #f6faf6;
                border: 1px solid #e3ebe3;
                border-radius: 24px;
            }
            QGroupBox#sectionPanel {
                margin-top: 10px;
                padding-top: 8px;
            }
            QGroupBox#sectionPanel::title {
                subcontrol-origin: margin;
                left: 18px;
                padding: 0 6px;
                color: #33483a;
                font-size: 13px;
                font-weight: 700;
            }
            QFrame#statCard {
                background: #f6faf6;
                border: 1px solid #e3ebe3;
                border-radius: 22px;
            }
            QLabel#statLabel {
                color: #55665a;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QLabel#statValue {
                color: #18241b;
                font-size: 34px;
                font-weight: 800;
            }
            QLabel#statHelper {
                color: #607064;
                font-size: 13px;
            }
            QLabel#sectionLabel {
                color: #33483a;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#summaryValue {
                color: #18241b;
                font-size: 24px;
                font-weight: 800;
            }
            QLabel#summarySubtext {
                color: #607064;
                font-size: 13px;
            }
            QLabel#statusBadge {
                background: #e8f6ec;
                color: #0a8c3c;
                border: 1px solid #cfe6d4;
                border-radius: 14px;
                padding: 8px 14px;
                font-size: 13px;
                font-weight: 700;
                min-height: 24px;
            }
            QPushButton#primaryButton {
                background: #0a8c3c;
                color: white;
                border: none;
                border-radius: 18px;
                padding: 10px 22px;
                font-size: 15px;
                font-weight: 800;
                min-height: 24px;
            }
            QPushButton#primaryButton:hover {
                background: #087632;
            }
            QPushButton#secondaryButton {
                background: #edf2ee;
                color: #294032;
                border: none;
                border-radius: 18px;
                padding: 10px 22px;
                font-size: 15px;
                font-weight: 700;
                min-height: 24px;
            }
            QPushButton#secondaryButton:hover {
                background: #e3ebe4;
            }
            QPushButton#dangerButton {
                background: #fbe9e7;
                color: #c0392b;
                border: none;
                border-radius: 18px;
                padding: 10px 22px;
                font-size: 15px;
                font-weight: 700;
                min-height: 24px;
            }
            QPushButton#dangerButton:hover {
                background: #f7dcd8;
            }
            QLineEdit, QTextEdit {
                background: #ffffff;
                color: #203126;
                border: 1px solid #d7e3d8;
                border-radius: 12px;
                padding: 10px 14px;
                font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #0b9b4a;
                background: #f7fbf8;
            }
            QScrollArea {
                border: none;
                background: transparent;
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

        side_terminal = QLabel("Super Admin Console")
        side_terminal.setObjectName("terminalName")
        side_layout.addWidget(side_terminal)

        side_layout.addSpacing(28)
        side_layout.addStretch()

        body_layout.addWidget(side_panel, 0, Qt.AlignTop)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(52, 42, 52, 42)
        card_layout.setSpacing(24)

        title = QLabel("Operations Analytics Center")
        title.setObjectName("cardTitle")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel(
            "Review queue health, service performance, and campus operations from one admin dashboard."
        )
        subtitle.setObjectName("cardSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        card_layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        card_layout.addWidget(self.tabs)

        self._build_overview_tab()
        self._build_queue_tab()
        self._build_settings_tab()

        body_layout.addWidget(card, 1)

    def _build_overview_tab(self):
        overview_tab = QWidget()
        layout = QVBoxLayout(overview_tab)
        layout.setSpacing(22)

        stat_grid = QGridLayout()
        stat_grid.setHorizontalSpacing(20)
        stat_grid.setVerticalSpacing(20)

        self.total_served_card = StatCard("TOTAL SERVED", 0, "#0a8c3c", "Completed service transactions")
        self.avg_wait_card = StatCard("AVG WAIT TIME", "0.0 min", "#e67e22", "Average delay before being called")
        self.waiting_card = StatCard("IN QUEUE", 0, "#1f6feb", "Students currently waiting")
        self.serving_card = StatCard("NOW SERVING", 0, "#8e44ad", "Tickets currently active at counters")

        stat_grid.addWidget(self.total_served_card, 0, 0)
        stat_grid.addWidget(self.avg_wait_card, 0, 1)
        stat_grid.addWidget(self.waiting_card, 1, 0)
        stat_grid.addWidget(self.serving_card, 1, 1)

        layout.addLayout(stat_grid)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(18)

        summary_panel = QFrame()
        summary_panel.setObjectName("sectionPanel")
        summary_layout = QVBoxLayout(summary_panel)
        summary_layout.setContentsMargins(24, 22, 24, 22)
        summary_layout.setSpacing(12)

        summary_label = QLabel("SERVICE SUMMARY")
        summary_label.setObjectName("sectionLabel")
        summary_layout.addWidget(summary_label)

        self.service_snapshot_value = QLabel("0.0 minutes")
        self.service_snapshot_value.setObjectName("summaryValue")
        summary_layout.addWidget(self.service_snapshot_value)

        self.service_snapshot_text = QLabel("Waiting for queue activity.")
        self.service_snapshot_text.setObjectName("summarySubtext")
        self.service_snapshot_text.setWordWrap(True)
        summary_layout.addWidget(self.service_snapshot_text)
        summary_layout.addStretch()

        bottom_row.addWidget(summary_panel, 1)

        queue_health_panel = QFrame()
        queue_health_panel.setObjectName("sectionPanel")
        queue_health_layout = QVBoxLayout(queue_health_panel)
        queue_health_layout.setContentsMargins(24, 22, 24, 22)
        queue_health_layout.setSpacing(12)

        queue_health_label = QLabel("QUEUE HEALTH")
        queue_health_label.setObjectName("sectionLabel")
        queue_health_layout.addWidget(queue_health_label)

        self.queue_health_value = QLabel("Stable")
        self.queue_health_value.setObjectName("summaryValue")
        queue_health_layout.addWidget(self.queue_health_value)

        self.queue_health_text = QLabel("No active congestion detected.")
        self.queue_health_text.setObjectName("summarySubtext")
        self.queue_health_text.setWordWrap(True)
        queue_health_layout.addWidget(self.queue_health_text)
        queue_health_layout.addStretch()

        bottom_row.addWidget(queue_health_panel, 1)
        layout.addLayout(bottom_row)

        counters_group = QGroupBox("Counter Station Status")
        counters_group.setObjectName("sectionPanel")
        counters_layout = QVBoxLayout(counters_group)
        counters_layout.setContentsMargins(18, 16, 18, 18)

        self.counter_table = QTableWidget()
        self.counter_table.setColumnCount(3)
        self.counter_table.setHorizontalHeaderLabels(["Counter", "Status", "Current Ticket"])
        self.counter_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.counter_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.counter_table.verticalHeader().setVisible(False)
        self.counter_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.counter_table.setMinimumHeight(220)
        counters_layout.addWidget(self.counter_table)

        layout.addWidget(counters_group)
        self.tabs.addTab(overview_tab, "Overview")

    def _build_queue_tab(self):
        queue_tab = QWidget()
        layout = QVBoxLayout(queue_tab)
        layout.setSpacing(22)

        action_row = QHBoxLayout()
        action_row.setSpacing(14)

        refresh_btn = QPushButton("REFRESH")
        refresh_btn.setObjectName("primaryButton")
        refresh_btn.clicked.connect(self._refresh_data)
        action_row.addWidget(refresh_btn)

        clear_btn = QPushButton("CLEAR COMPLETED")
        clear_btn.setObjectName("dangerButton")
        clear_btn.clicked.connect(self._clear_completed)
        action_row.addWidget(clear_btn)

        export_btn = QPushButton("EXPORT DATA")
        export_btn.setObjectName("secondaryButton")
        export_btn.clicked.connect(self._export_stats)
        action_row.addWidget(export_btn)

        reset_btn = QPushButton("RESET STATISTICS")
        reset_btn.setObjectName("secondaryButton")
        reset_btn.clicked.connect(self._reset_statistics)
        action_row.addWidget(reset_btn)
        action_row.addStretch()

        layout.addLayout(action_row)

        queue_group = QGroupBox("Active Queue Monitor")
        queue_group.setObjectName("sectionPanel")
        queue_layout = QVBoxLayout(queue_group)
        queue_layout.setContentsMargins(18, 16, 18, 18)

        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(7)
        self.queue_table.setHorizontalHeaderLabels(
            ["Ticket #", "Name", "Student ID", "Purpose", "Visitor", "Status", "Created"]
        )
        self.queue_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.queue_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.queue_table.verticalHeader().setVisible(False)
        self.queue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.queue_table.horizontalHeader().setMinimumSectionSize(120)
        self.queue_table.setMinimumHeight(360)
        queue_layout.addWidget(self.queue_table)

        layout.addWidget(queue_group)
        self.tabs.addTab(queue_tab, "Queue")

    def _build_settings_tab(self):
        settings_tab = QWidget()
        tab_layout = QVBoxLayout(settings_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 10, 20, 20)
        layout.setSpacing(22)

        # 1. Kiosk Settings Group
        kiosk_group = QGroupBox("Student Kiosk Settings")
        kiosk_group.setObjectName("sectionPanel")
        kiosk_layout = QVBoxLayout(kiosk_group)
        kiosk_layout.setContentsMargins(22, 18, 22, 22)
        kiosk_layout.setSpacing(16)

        kiosk_intro = QLabel("Control optional fields shown on the student check-in screen.")
        kiosk_intro.setObjectName("summarySubtext")
        kiosk_intro.setWordWrap(True)
        kiosk_layout.addWidget(kiosk_intro)

        self.phone_field_status = QLabel()
        self.phone_field_status.setObjectName("statusBadge")
        self.phone_field_status.setWordWrap(True)
        kiosk_layout.addWidget(self.phone_field_status)

        kiosk_button_row = QHBoxLayout()
        kiosk_button_row.setSpacing(14)

        self.phone_toggle_btn = QPushButton()
        self.phone_toggle_btn.setObjectName("primaryButton")
        self.phone_toggle_btn.setMinimumHeight(44)
        self.phone_toggle_btn.clicked.connect(self._toggle_phone_number_field)
        kiosk_button_row.addWidget(self.phone_toggle_btn)
        kiosk_button_row.addStretch()

        kiosk_layout.addLayout(kiosk_button_row)
        layout.addWidget(kiosk_group)

        # 2. Telegram QR Bot System Configuration Group
        telegram_group = QGroupBox("Telegram QR Bot System Configuration")
        telegram_group.setObjectName("sectionPanel")
        telegram_layout = QVBoxLayout(telegram_group)
        telegram_layout.setContentsMargins(22, 18, 22, 22)
        telegram_layout.setSpacing(18)

        telegram_intro = QLabel(
            "Official Telegram Bot API integration with QR deep-linking for queue alerts. "
            "Includes dedicated Capstone Mock Mode for local offline defense demonstrations without requiring an active bot token."
        )
        telegram_intro.setObjectName("summarySubtext")
        telegram_intro.setWordWrap(True)
        telegram_layout.addWidget(telegram_intro)

        # Status badge
        self.telegram_status_badge = QLabel()
        self.telegram_status_badge.setObjectName("statusBadge")
        self.telegram_status_badge.setWordWrap(True)
        telegram_layout.addWidget(self.telegram_status_badge)

        # Button controls
        tg_button_row = QHBoxLayout()
        tg_button_row.setSpacing(12)

        self.tg_master_toggle_btn = QPushButton()
        self.tg_master_toggle_btn.setMinimumHeight(44)
        self.tg_master_toggle_btn.clicked.connect(self._toggle_telegram_master)
        tg_button_row.addWidget(self.tg_master_toggle_btn)

        self.tg_mode_toggle_btn = QPushButton()
        self.tg_mode_toggle_btn.setMinimumHeight(44)
        self.tg_mode_toggle_btn.clicked.connect(self._toggle_telegram_mode)
        tg_button_row.addWidget(self.tg_mode_toggle_btn)

        self.tg_test_btn = QPushButton("TEST TELEGRAM DISPATCH")
        self.tg_test_btn.setObjectName("secondaryButton")
        self.tg_test_btn.setMinimumHeight(44)
        self.tg_test_btn.clicked.connect(self._test_telegram_dispatch)
        tg_button_row.addWidget(self.tg_test_btn)

        self.tg_logs_btn = QPushButton("VIEW MOCK TELEGRAM LOGS")
        self.tg_logs_btn.setObjectName("secondaryButton")
        self.tg_logs_btn.setMinimumHeight(44)
        self.tg_logs_btn.clicked.connect(self._view_telegram_logs)
        tg_button_row.addWidget(self.tg_logs_btn)

        tg_button_row.addStretch()
        telegram_layout.addLayout(tg_button_row)

        # Credentials & Bot Info
        tg_cred_label = QLabel("BOT CREDENTIALS & DEEP LINKING")
        tg_cred_label.setObjectName("sectionLabel")
        telegram_layout.addWidget(tg_cred_label)

        tg_cred_row = QHBoxLayout()
        tg_cred_row.setSpacing(24)

        tg_inputs_col = QVBoxLayout()
        tg_inputs_col.setSpacing(12)

        token_lbl = QLabel("Telegram Bot Token (from @BotFather):")
        token_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        self.tg_token_input = QLineEdit()
        self.tg_token_input.setPlaceholderText("e.g. 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ (Optional in Mock Mode)")
        self.tg_token_input.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        tg_inputs_col.addWidget(token_lbl)
        tg_inputs_col.addWidget(self.tg_token_input)

        user_lbl = QLabel("Telegram Bot Username:")
        user_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        self.tg_username_input = QLineEdit()
        self.tg_username_input.setPlaceholderText(
            "Auto-detected from your token when you SAVE in Live Mode (no typing needed)"
        )
        self.tg_username_input.textChanged.connect(self._update_telegram_qr_preview)
        tg_inputs_col.addWidget(user_lbl)
        tg_inputs_col.addWidget(self.tg_username_input)

        tg_cred_row.addLayout(tg_inputs_col, 2)

        # Live QR code preview card
        qr_preview_card = QFrame()
        qr_preview_card.setStyleSheet(
            "background: #ffffff; border: 1px solid #e3ebe3; border-radius: 18px; padding: 12px;"
        )
        qr_card_layout = QVBoxLayout(qr_preview_card)
        qr_card_layout.setContentsMargins(12, 10, 12, 10)
        qr_card_layout.setSpacing(6)
        qr_card_layout.setAlignment(Qt.AlignCenter)

        self.tg_qr_preview_label = QLabel()
        self.tg_qr_preview_label.setAlignment(Qt.AlignCenter)
        self.tg_qr_link_label = QLabel()
        self.tg_qr_link_label.setAlignment(Qt.AlignCenter)
        self.tg_qr_link_label.setStyleSheet("color: #0088cc; font-size: 11px; font-weight: 700;")
        qr_card_layout.addWidget(self.tg_qr_preview_label)
        qr_card_layout.addWidget(self.tg_qr_link_label)

        tg_cred_row.addWidget(qr_preview_card, 1)
        telegram_layout.addLayout(tg_cred_row)

        # Notification Templates
        tg_tmpl_label = QLabel("TELEGRAM NOTIFICATION TEMPLATES (Markdown Supported)")
        tg_tmpl_label.setObjectName("sectionLabel")
        telegram_layout.addWidget(tg_tmpl_label)

        tg_tmpl_hint = QLabel("Dynamic tags supported: {name}, {ticket}, {position}, {purpose}, {counter}")
        tg_tmpl_hint.setObjectName("summarySubtext")
        telegram_layout.addWidget(tg_tmpl_hint)

        tg_tmpl_col = QVBoxLayout()
        tg_tmpl_col.setSpacing(12)

        tg_t1_lbl = QLabel("1. Ticket Created Alert (Dispatched on Kiosk Registration):")
        tg_t1_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        self.tg_created_tmpl_input = QLineEdit()
        tg_tmpl_col.addWidget(tg_t1_lbl)
        tg_tmpl_col.addWidget(self.tg_created_tmpl_input)

        tg_t2_lbl = QLabel("2. Ticket Called Alert (Dispatched when Service Counter calls/recalls ticket):")
        tg_t2_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        self.tg_called_tmpl_input = QLineEdit()
        tg_tmpl_col.addWidget(tg_t2_lbl)
        tg_tmpl_col.addWidget(self.tg_called_tmpl_input)

        tg_t3_lbl = QLabel("3. Ticket Completed Alert (Dispatched when Service Counter marks ticket Done):")
        tg_t3_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        self.tg_completed_tmpl_input = QLineEdit()
        tg_tmpl_col.addWidget(tg_t3_lbl)
        tg_tmpl_col.addWidget(self.tg_completed_tmpl_input)

        telegram_layout.addLayout(tg_tmpl_col)

        # Save Button Row
        tg_save_row = QHBoxLayout()
        self.tg_save_btn = QPushButton("SAVE TELEGRAM CONFIGURATION")
        self.tg_save_btn.setObjectName("primaryButton")
        self.tg_save_btn.setMinimumHeight(46)
        self.tg_save_btn.clicked.connect(self._save_telegram_settings)
        tg_save_row.addWidget(self.tg_save_btn)
        tg_save_row.addStretch()
        telegram_layout.addLayout(tg_save_row)

        layout.addWidget(telegram_group)
        layout.addStretch()

        scroll.setWidget(container)
        tab_layout.addWidget(scroll)
        self.tabs.addTab(settings_tab, "Settings")

    def _setup_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_data)
        self.refresh_timer.start(5000)
        self._refresh_data()

    def _update_phone_toggle_ui(self):
        settings = self.db.get_app_settings()
        enabled = settings.get("phone_number_enabled", True)

        if enabled:
            self.phone_field_status.setText("Phone number field is VISIBLE on the student kiosk.")
            self.phone_toggle_btn.setText("DISABLE PHONE NUMBER")
            self.phone_toggle_btn.setObjectName("dangerButton")
        else:
            self.phone_field_status.setText("Phone number field is HIDDEN on the student kiosk.")
            self.phone_toggle_btn.setText("ENABLE PHONE NUMBER")
            self.phone_toggle_btn.setObjectName("primaryButton")

        self.phone_toggle_btn.style().unpolish(self.phone_toggle_btn)
        self.phone_toggle_btn.style().polish(self.phone_toggle_btn)

    def _toggle_phone_number_field(self):
        settings = self.db.get_app_settings()
        enabled = settings.get("phone_number_enabled", True)
        self.db.set_phone_number_enabled(not enabled)
        self._update_phone_toggle_ui()
        state = "visible" if not enabled else "hidden"
        QMessageBox.information(
            self,
            "Student Kiosk Updated",
            f"The phone number field is now {state} on the student kiosk.",
        )

    def _update_telegram_ui(self):
        tg = self.db.get_telegram_settings()
        enabled = tg.get("telegram_enabled", True)
        mock = tg.get("telegram_mock_mode", True)
        token = tg.get("telegram_bot_token", "").strip()
        username = tg.get("telegram_bot_username", "TapNQueBot").strip()

        if not enabled:
            self.telegram_status_badge.setText("○ TELEGRAM BOT SYSTEM DISABLED — Notifications will not be dispatched.")
            self.telegram_status_badge.setStyleSheet(
                "background: #f1f3f4; color: #5f6368; border: 1px solid #dadce0; border-radius: 14px; padding: 10px 16px; font-weight: 700; font-size: 14px;"
            )
            self.tg_master_toggle_btn.setText("ENABLE TELEGRAM SYSTEM")
            self.tg_master_toggle_btn.setObjectName("primaryButton")
            self.tg_mode_toggle_btn.setEnabled(False)
        elif mock:
            self.telegram_status_badge.setText(
                "● MOCK MODE ACTIVE (Safe Capstone Simulation — Local Telegram Dispatches & Mock Logs Active)"
            )
            self.telegram_status_badge.setStyleSheet(
                "background: #e8f0fe; color: #1967d2; border: 1px solid #aecbfa; border-radius: 14px; padding: 10px 16px; font-weight: 700; font-size: 14px;"
            )
            self.tg_master_toggle_btn.setText("DISABLE TELEGRAM")
            self.tg_master_toggle_btn.setObjectName("dangerButton")
            self.tg_mode_toggle_btn.setText("SWITCH TO LIVE BOT")
            self.tg_mode_toggle_btn.setObjectName("secondaryButton")
            self.tg_mode_toggle_btn.setEnabled(True)
        else:
            if token:
                self.telegram_status_badge.setText("● LIVE TELEGRAM BOT ACTIVE (Official api.telegram.org Dispatches)")
                self.telegram_status_badge.setStyleSheet(
                    "background: #e6f4ea; color: #137333; border: 1px solid #ceead6; border-radius: 14px; padding: 10px 16px; font-weight: 700; font-size: 14px;"
                )
            else:
                self.telegram_status_badge.setText(
                    "● LIVE BOT SELECTED — BOT TOKEN MISSING (Dispatches are simulated locally until a token is saved)"
                )
                self.telegram_status_badge.setStyleSheet(
                    "background: #fef7e0; color: #b05c00; border: 1px solid #f5c37d; border-radius: 14px; padding: 10px 16px; font-weight: 700; font-size: 14px;"
                )
            self.tg_master_toggle_btn.setText("DISABLE TELEGRAM")
            self.tg_master_toggle_btn.setObjectName("dangerButton")
            self.tg_mode_toggle_btn.setText("SWITCH TO MOCK SIMULATION")
            self.tg_mode_toggle_btn.setObjectName("secondaryButton")
            self.tg_mode_toggle_btn.setEnabled(True)

        self.tg_master_toggle_btn.style().unpolish(self.tg_master_toggle_btn)
        self.tg_master_toggle_btn.style().polish(self.tg_master_toggle_btn)
        self.tg_mode_toggle_btn.style().unpolish(self.tg_mode_toggle_btn)
        self.tg_mode_toggle_btn.style().polish(self.tg_mode_toggle_btn)

        self.tg_token_input.setText(tg.get("telegram_bot_token", ""))
        self.tg_username_input.setText(username)
        self.tg_created_tmpl_input.setText(tg.get("telegram_template_created", ""))
        self.tg_called_tmpl_input.setText(tg.get("telegram_template_called", ""))
        self.tg_completed_tmpl_input.setText(tg.get("telegram_template_completed", ""))

        self._update_telegram_qr_preview()

    def _update_telegram_qr_preview(self):
        username = self.tg_username_input.text().strip().lstrip("@")
        if not username:
            self.tg_qr_preview_label.clear()
            self.tg_qr_preview_label.setText(
                "No bot configured yet.\nSave a valid Bot Token in Live Mode —\n"
                "the username and this QR then fill in automatically."
            )
            self.tg_qr_preview_label.setWordWrap(True)
            self.tg_qr_preview_label.setStyleSheet("color: #5f6368; font-size: 12px;")
            self.tg_qr_link_label.setText("")
            return
        self.tg_qr_preview_label.setStyleSheet("")
        bot_url = f"https://t.me/{username}"
        pixmap = generate_telegram_qr_pixmap(bot_url, size=110)
        if pixmap and not pixmap.isNull():
            self.tg_qr_preview_label.setPixmap(pixmap)
        self.tg_qr_link_label.setText(f"@{username}\n{bot_url}")

    def _toggle_telegram_master(self):
        tg = self.db.get_telegram_settings()
        new_state = not tg.get("telegram_enabled", True)
        self.db.set_telegram_enabled(new_state)
        self._update_telegram_ui()
        state_str = "ENABLED" if new_state else "DISABLED"
        QMessageBox.information(
            self,
            "Telegram System Status",
            f"Telegram notification subsystem is now {state_str}.",
        )

    def _toggle_telegram_mode(self):
        tg = self.db.get_telegram_settings()
        current_mock = tg.get("telegram_mock_mode", True)
        new_mock = not current_mock
        self.db.set_telegram_mock_mode(new_mock)
        self._update_telegram_ui()
        if new_mock:
            QMessageBox.information(
                self,
                "Mock Mode Active",
                "Switched to Safe Mock Mode.\nAll Telegram messages will be simulated locally and recorded in Mock Logs.",
            )
        else:
            QMessageBox.information(
                self,
                "Live Mode Active",
                "Switched to Live Telegram Bot Mode.\nMessages will be dispatched directly to Telegram API if a Bot Token is configured.",
            )

    def _save_telegram_settings(self):
        token = self.tg_token_input.text().strip()
        username = self.tg_username_input.text().strip().lstrip("@")
        created_tmpl = self.tg_created_tmpl_input.text().strip()
        called_tmpl = self.tg_called_tmpl_input.text().strip()
        completed_tmpl = self.tg_completed_tmpl_input.text().strip()

        tg = self.db.get_telegram_settings()
        wants_live = tg.get("telegram_enabled", True) and not tg.get("telegram_mock_mode", True)

        detected_username = None
        validation_error = None
        if token and wants_live:
            # One-tap setup: validate the token and auto-detect the bot username
            # so the admin never has to find or type it manually.
            ok, detected_username, validation_error = validate_telegram_bot_token(token)
            if ok and detected_username:
                if detected_username.lower() != username.lower():
                    username = detected_username
                validation_error = None
            elif not ok:
                detected_username = None

        self.db.save_telegram_settings(
            bot_token=token,
            bot_username=username,
            template_created=created_tmpl,
            template_called=called_tmpl,
            template_completed=completed_tmpl,
        )
        self._update_telegram_ui()

        if wants_live and token:
            ensure_link_listener()

        if detected_username:
            QMessageBox.information(
                self,
                "Connected — Setup Complete",
                f"✅ Connected to Telegram as @{detected_username}.\n\n"
                f"Everything is now automatic:\n"
                f"• The kiosk QR code encodes your bot's link\n"
                f"• Students scan it and tap START — no typing\n"
                f"• Their ticket links itself and alerts begin flowing\n\n"
                f"Use TEST TELEGRAM DISPATCH to verify end-to-end delivery.",
            )
        elif token and wants_live and validation_error:
            QMessageBox.warning(
                self,
                "Settings Saved — Token Check Failed",
                f"Configuration was saved, but the bot token could not be verified:\n\n"
                f"{validation_error}\n\n"
                f"QR scanning and live alerts will not work until a valid token is saved.",
            )
        else:
            QMessageBox.information(
                self,
                "Settings Saved",
                "Telegram Bot configuration and message templates have been successfully updated.",
            )

    def _test_telegram_dispatch(self):
        tg = self.db.get_telegram_settings()
        is_mock = tg.get("telegram_mock_mode", True)
        bot_token = tg.get("telegram_bot_token", "").strip()
        bot_username = (tg.get("telegram_bot_username", "") or "").strip().lstrip("@") or "your TapNQue bot"

        recent_users = fetch_recent_telegram_users(bot_token) if bot_token else []

        if recent_users:
            latest = recent_users[0]
            default_text = latest["chat_id"]
            user_label = f"{latest['display_name']}"
            if latest["username"]:
                user_label += f" (@{latest['username']})"
            prompt_desc = (
                f"Enter recipient Telegram Chat ID or Username:\n\n"
                f"✅ Active user detected from /start: {user_label}\n"
                f"(Chat ID: {latest['chat_id']})\n\n"
                f"Click OK to dispatch test alert, or enter another recipient:"
            )
        else:
            default_text = ""
            prompt_desc = (
                f"Enter recipient Telegram Chat ID:\n\n"
                f"ℹ️ Ensure the recipient has opened {bot_username if bot_username.startswith('your') else '@' + bot_username} "
                f"in Telegram and tapped START.\n\n"
                f"Enter your numeric Chat ID (obtain it via @userinfobot)\n"
                f"or your @username (if you already tapped START):"
            )

        chat_id, ok = QInputDialog.getText(
            self,
            "Test Telegram Dispatch",
            prompt_desc,
            text=default_text,
        )
        if not ok or not chat_id.strip():
            return

        chat_id = chat_id.strip()
        test_msg = "🔔 *TapNQue Test Alert*\n\nThis is a test notification verifying your Telegram Bot integration."

        if is_mock or not bot_token:
            simulate_mock_telegram(chat_id, test_msg, "test", 9999)
            QMessageBox.information(
                self,
                "Test Dispatched (Mock Simulation)",
                f"Simulated Telegram message to {chat_id} recorded in Mock Logs.\n\nContent:\n{test_msg}",
            )
        else:
            success, status, err = send_via_telegram_api(chat_id, test_msg, bot_token)
            if success:
                QMessageBox.information(
                    self,
                    "Live Telegram Dispatch Successful",
                    f"Message successfully sent via Telegram Bot API to {chat_id}!\n\nStatus: {status}",
                )
            else:
                QMessageBox.warning(
                    self,
                    "Live Telegram Dispatch Failed",
                    f"Failed to dispatch to Telegram API:\n{err}",
                )

    def _view_telegram_logs(self):
        dlg = TelegramLogDialog(self)
        dlg.populate_logs(get_mock_telegram_history())

        def _clear():
            reply = QMessageBox.question(
                dlg,
                "Clear Logs",
                "Are you sure you want to clear the session mock Telegram logs?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                clear_mock_telegram_history()
                dlg.populate_logs([])

        def _refresh():
            dlg.populate_logs(get_mock_telegram_history())

        dlg.clear_btn.clicked.connect(_clear)
        dlg.refresh_btn.clicked.connect(_refresh)
        dlg.exec()

    def _format_counter_ticket(self, ticket: Any) -> str:
        if isinstance(ticket, int):
            return f"#{ticket:04d}"
        return "None"

    def _update_counter_table(self, counters: list):
        self.counter_table.setRowCount(len(counters))
        for row, counter in enumerate(counters):
            name_item = QTableWidgetItem(counter.get("name", "Counter"))
            status_text = counter.get("status", "unknown").capitalize()
            status_item = QTableWidgetItem(status_text)
            if counter.get("status") == "busy":
                status_item.setForeground(QColor("#c0392b"))
            else:
                status_item.setForeground(QColor("#0a8c3c"))

            ticket_item = QTableWidgetItem(self._format_counter_ticket(counter.get("current_ticket")))
            self.counter_table.setItem(row, 0, name_item)
            self.counter_table.setItem(row, 1, status_item)
            self.counter_table.setItem(row, 2, ticket_item)

    def _update_queue_table(self, tickets: list):
        self.queue_table.setRowCount(len(tickets))
        for row, ticket in enumerate(tickets):
            created_str = ""
            if ticket.get("created_at"):
                try:
                    created_dt = datetime.fromisoformat(ticket["created_at"])
                    created_str = created_dt.strftime("%Y-%m-%d %I:%M %p")
                except Exception:
                    created_str = str(ticket.get("created_at"))

            self.queue_table.setItem(row, 0, QTableWidgetItem(f"#{ticket['ticket_number']:04d}"))
            self.queue_table.setItem(row, 1, QTableWidgetItem(ticket.get("name", "")))
            self.queue_table.setItem(row, 2, QTableWidgetItem(ticket.get("student_id", "")))
            self.queue_table.setItem(row, 3, QTableWidgetItem(ticket.get("purpose", "")))
            self.queue_table.setItem(row, 4, QTableWidgetItem(ticket.get("visitor_type", "")))

            status_text = ticket.get("status", "").capitalize()
            status_item = QTableWidgetItem(status_text)
            if ticket.get("status") in {"serving", "recalled"}:
                status_item.setForeground(QColor("#0a8c3c"))
            else:
                status_item.setForeground(QColor("#1f6feb"))
            self.queue_table.setItem(row, 5, status_item)
            self.queue_table.setItem(row, 6, QTableWidgetItem(created_str))

    def _update_analytics_summary(self, stats: dict, waiting: list, serving: list, counters: list):
        total = stats.get("total_served", 0)
        avg_wait_seconds = stats.get("average_wait_time", 0.0) or 0.0
        avg_minutes = avg_wait_seconds / 60

        self.total_served_card.update_value(total)
        self.total_served_card.update_helper("Completed service transactions")

        self.avg_wait_card.update_value(f"{avg_minutes:.1f} min")
        if total:
            self.avg_wait_card.update_helper("Calculated from completed queue tickets")
        else:
            self.avg_wait_card.update_helper("Average will appear after completed tickets")

        self.waiting_card.update_value(len(waiting))
        self.waiting_card.update_helper("Students currently waiting")

        self.serving_card.update_value(len(serving))
        busy_count = sum(1 for counter in counters if counter.get("status") == "busy")
        self.serving_card.update_helper(f"{busy_count} counter(s) actively serving")

        total_wait_minutes = stats.get("total_wait_time", 0.0) / 60 if stats.get("total_wait_time", 0.0) else 0.0
        self.service_snapshot_value.setText(f"{total_wait_minutes:.1f} minutes")
        self.service_snapshot_text.setText(
            f"Total accumulated wait time across {total} served ticket(s)."
        )

        if len(waiting) >= 8:
            self.queue_health_value.setText("High Load")
            self.queue_health_text.setText("Queue is building up. Consider opening more counters.")
        elif len(waiting) >= 4:
            self.queue_health_value.setText("Moderate")
            self.queue_health_text.setText("Traffic is steady and should be monitored closely.")
        else:
            self.queue_health_value.setText("Stable")
            self.queue_health_text.setText("Queue pressure is low and counters look manageable.")

    def _refresh_data(self):
        try:
            stats = self.db.get_statistics()
            waiting = self.db.get_waiting_queue()
            serving = self.db.get_currently_serving()
            counters = self.db.get_counters()

            all_tickets = waiting + serving
            all_tickets.sort(key=lambda ticket: ticket.get("ticket_number", 0))

            self._update_analytics_summary(stats, waiting, serving, counters)
            self._update_counter_table(counters)
            self._update_queue_table(all_tickets)
        except Exception as exc:
            print(f"Error refreshing data: {exc}")

    def _clear_completed(self):
        reply = QMessageBox.question(
            self,
            "Clear Completed",
            "Are you sure you want to permanently delete all completed tickets from the database?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            deleted_count = self.db.clear_completed_tickets()
            QMessageBox.information(
                self,
                "Success",
                f"Completed tickets cleared successfully ({deleted_count} records removed).",
            )
            self._refresh_data()

    def _reset_statistics(self):
        reply = QMessageBox.warning(
            self,
            "Reset Statistics",
            "Are you sure you want to RESET all statistics?\nThis action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.db.reset_statistics()
            QMessageBox.information(self, "Success", "Statistics have been reset!")
            self._refresh_data()

    def _export_stats(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Statistics",
            f"kiosk_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)",
        )

        if not file_path:
            return

        stats = self.db.get_statistics()
        waiting = self.db.get_waiting_queue()
        serving = self.db.get_currently_serving()
        served = self.db.get_served_tickets()

        export_data = {
            "exported_at": datetime.now().isoformat(),
            "statistics": stats,
            "waiting_queue": waiting,
            "currently_serving": serving,
            "served_history": served,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)

        QMessageBox.information(self, "Success", f"Statistics exported to:\n{file_path}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = SuperAdmin()
    if getattr(window, "authenticated", False):
        window.show()
    else:
        sys.exit(0)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
