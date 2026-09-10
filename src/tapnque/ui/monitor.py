"""
Live Display Monitor for Waiting Area.
Large TV-friendly queue display for students and visitors with theme toggle.
"""

import sys
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from tapnque.core.database import get_database


class TicketCard(QFrame):
    """Compact ticket card for the upcoming queue list."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("ticketCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        self.position_label = QLabel("UP NEXT")
        self.position_label.setObjectName("cardEyebrow")
        layout.addWidget(self.position_label)

        self.ticket_label = QLabel("--")
        self.ticket_label.setObjectName("cardTicket")
        layout.addWidget(self.ticket_label)

        self.purpose_label = QLabel("Waiting for new ticket")
        self.purpose_label.setObjectName("cardPurpose")
        self.purpose_label.setWordWrap(True)
        layout.addWidget(self.purpose_label)

        self.wait_label = QLabel("0 min wait")
        self.wait_label.setObjectName("cardMeta")
        layout.addWidget(self.wait_label)

    def set_ticket(self, position: int, ticket: dict):
        self.position_label.setText(f"UP NEXT {position}")
        self.ticket_label.setText(f"#{ticket['ticket_number']:04d}")
        self.purpose_label.setText(ticket.get("purpose", "No purpose set"))

        try:
            created = datetime.fromisoformat(ticket["created_at"])
            wait_minutes = int((datetime.now() - created).total_seconds() / 60)
            self.wait_label.setText(f"{max(0, wait_minutes)} min wait")
        except Exception:
            self.wait_label.setText("Stand by")
        self.show()

    def set_empty(self, position: int):
        self.position_label.setText(f"UP NEXT {position}")
        self.ticket_label.setText("--")
        self.purpose_label.setText("Waiting for new ticket")
        self.wait_label.setText("Stand by")
        self.show()


class LiveDisplayMonitor(QWidget):
    """Public display window for showing the live ticket queue."""

    def __init__(self):
        super().__init__()
        self.db = get_database()
        self.ticket_cards = []
        self._pulse_on = False
        self.theme_mode = "dark"
        self._setup_ui()
        self._apply_theme()
        self._setup_timers()
        self._refresh_display()

    def _build_stylesheet(self) -> str:
        if self.theme_mode == "light":
            return """
            QWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #f4f7f4,
                    stop: 0.55 #edf3ee,
                    stop: 1 #e4ede6
                );
                color: #203126;
                font-family: "Segoe UI";
            }
            QLabel {
                background: transparent;
            }
            QFrame#shellPanel {
                background: rgba(248, 251, 248, 0.9);
                border: 1px solid #d7e3d8;
                border-radius: 36px;
            }
            QFrame#heroCard, QFrame#queueCard, QFrame#statsCard, QFrame#ticketCard {
                background: rgba(255, 255, 255, 0.98);
                border: 1px solid #dfe9e0;
                border-radius: 30px;
            }
            QFrame#heroCard[pulse="true"] {
                border: 3px solid #0b9b4a;
            }
            QLabel#topEyebrow {
                color: #0b9b4a;
                font-size: 17px;
                font-weight: 800;
                letter-spacing: 3px;
            }
            QLabel#pageTitle {
                color: #18241b;
                font-size: 32px;
                font-weight: 900;
            }
            QLabel#pageSubtitle {
                color: #55665a;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel#clockLabel {
                color: #18241b;
                font-size: 21px;
                font-weight: 800;
            }
            QLabel#dateLabel {
                color: #607064;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#heroLabel {
                color: #0b9b4a;
                font-size: 28px;
                font-weight: 800;
                letter-spacing: 4px;
            }
            QLabel#heroTicket {
                color: #0a8c3c;
                font-size: 150px;
                font-weight: 900;
            }
            QLabel#heroPurpose {
                color: #304336;
                font-size: 21px;
                font-weight: 600;
            }
            QLabel#heroHint {
                color: #607064;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel#panelTitle {
                color: #18241b;
                font-size: 20px;
                font-weight: 800;
                letter-spacing: 1px;
            }
            QLabel#panelSubtitle {
                color: #607064;
                font-size: 13px;
            }
            QLabel#statValue {
                color: #0a8c3c;
                font-size: 38px;
                font-weight: 900;
            }
            QLabel#statLabel {
                color: #33483a;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 2px;
            }
            QLabel#statHelper {
                color: #607064;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#cardEyebrow {
                color: #0b9b4a;
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 2px;
            }
            QLabel#cardTicket {
                color: #18241b;
                font-size: 42px;
                font-weight: 900;
            }
            QLabel#cardPurpose {
                color: #304336;
                font-size: 15px;
                font-weight: 600;
            }
            QLabel#cardMeta {
                color: #607064;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#themeToggle {
                background: #edf2ee;
                color: #203126;
                border: 1px solid #d7e3d8;
                border-radius: 16px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton#themeToggle:hover {
                background: #e3ebe4;
            }
            """

        return """
            QWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #06110b,
                    stop: 0.45 #0a1710,
                    stop: 1 #102118
                );
                color: #eef7ef;
                font-family: "Segoe UI";
            }
            QLabel {
                background: transparent;
            }
            QFrame#shellPanel {
                background: rgba(11, 22, 16, 0.92);
                border: 1px solid rgba(92, 132, 108, 0.42);
                border-radius: 36px;
            }
            QFrame#heroCard, QFrame#queueCard, QFrame#statsCard, QFrame#ticketCard {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #102419,
                    stop: 0.55 #142d20,
                    stop: 1 #193726
                );
                border: 1px solid rgba(96, 147, 113, 0.32);
                border-radius: 30px;
            }
            QFrame#heroCard[pulse="true"] {
                border: 3px solid #3dd27b;
            }
            QLabel#topEyebrow {
                color: #46d784;
                font-size: 17px;
                font-weight: 800;
                letter-spacing: 3px;
            }
            QLabel#pageTitle {
                color: #f4fbf5;
                font-size: 32px;
                font-weight: 900;
            }
            QLabel#pageSubtitle {
                color: #a7c0af;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel#clockLabel {
                color: #f4fbf5;
                font-size: 21px;
                font-weight: 800;
            }
            QLabel#dateLabel {
                color: #8fac98;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#heroLabel {
                color: #6ae29a;
                font-size: 28px;
                font-weight: 800;
                letter-spacing: 4px;
            }
            QLabel#heroTicket {
                color: #ffffff;
                font-size: 150px;
                font-weight: 900;
            }
            QLabel#heroPurpose {
                color: #e2efe4;
                font-size: 21px;
                font-weight: 600;
            }
            QLabel#heroHint {
                color: #8fac98;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel#panelTitle {
                color: #f0f8f1;
                font-size: 20px;
                font-weight: 800;
                letter-spacing: 1px;
            }
            QLabel#panelSubtitle {
                color: #9eb8a7;
                font-size: 13px;
            }
            QLabel#statValue {
                color: #4dd38a;
                font-size: 38px;
                font-weight: 900;
            }
            QLabel#statLabel {
                color: #d8e9db;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 2px;
            }
            QLabel#statHelper {
                color: #8fac98;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#cardEyebrow {
                color: #5ed78f;
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 2px;
            }
            QLabel#cardTicket {
                color: #ffffff;
                font-size: 42px;
                font-weight: 900;
            }
            QLabel#cardPurpose {
                color: #d7e8db;
                font-size: 15px;
                font-weight: 600;
            }
            QLabel#cardMeta {
                color: #93b19d;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#themeToggle {
                background: rgba(18, 37, 27, 0.96);
                color: #eef7ef;
                border: 1px solid rgba(93, 143, 110, 0.5);
                border-radius: 16px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton#themeToggle:hover {
                background: rgba(27, 51, 38, 0.98);
            }
            """

    def _apply_theme(self):
        self.setStyleSheet(self._build_stylesheet())
        if hasattr(self, "theme_toggle_btn"):
            next_mode = "Light" if self.theme_mode == "dark" else "Dark"
            self.theme_toggle_btn.setText(f"Switch to {next_mode}")

    def _setup_ui(self):
        self.setWindowTitle("Live Display Monitor")
        self.setMinimumSize(1280, 720)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(0)

        shell_panel = QFrame()
        shell_panel.setObjectName("shellPanel")
        shell_layout = QVBoxLayout(shell_panel)
        shell_layout.setContentsMargins(18, 18, 18, 18)
        shell_layout.setSpacing(16)
        root_layout.addWidget(shell_panel)

        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        title_block = QVBoxLayout()
        title_block.setSpacing(4)

        eyebrow = QLabel("TAPNQUE LIVE DISPLAY")
        eyebrow.setObjectName("topEyebrow")
        title_block.addWidget(eyebrow)

        title = QLabel("Student Queue Monitor")
        title.setObjectName("pageTitle")
        title_block.addWidget(title)

        subtitle = QLabel("Please prepare your ticket and proceed when your number appears.")
        subtitle.setObjectName("pageSubtitle")
        title_block.addWidget(subtitle)

        top_row.addLayout(title_block)
        top_row.addStretch()

        self.theme_toggle_btn = QPushButton()
        self.theme_toggle_btn.setObjectName("themeToggle")
        self.theme_toggle_btn.clicked.connect(self._toggle_theme)
        top_row.addWidget(self.theme_toggle_btn)

        clock_block = QVBoxLayout()
        clock_block.setSpacing(2)

        self.clock_label = QLabel("--:-- --")
        self.clock_label.setObjectName("clockLabel")
        self.clock_label.setAlignment(Qt.AlignRight)
        clock_block.addWidget(self.clock_label)

        self.date_label = QLabel("--")
        self.date_label.setObjectName("dateLabel")
        self.date_label.setAlignment(Qt.AlignRight)
        clock_block.addWidget(self.date_label)

        top_row.addLayout(clock_block)
        shell_layout.addLayout(top_row)

        content_row = QHBoxLayout()
        content_row.setSpacing(18)

        self.hero_card = QFrame()
        self.hero_card.setObjectName("heroCard")
        hero_layout = QVBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(28, 24, 28, 24)
        hero_layout.setSpacing(12)

        hero_label = QLabel("NOW SERVING")
        hero_label.setObjectName("heroLabel")
        hero_label.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(hero_label)

        self.hero_ticket = QLabel("--")
        self.hero_ticket.setObjectName("heroTicket")
        self.hero_ticket.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(self.hero_ticket, 1)

        self.hero_purpose = QLabel("Waiting for the next ticket")
        self.hero_purpose.setObjectName("heroPurpose")
        self.hero_purpose.setAlignment(Qt.AlignCenter)
        self.hero_purpose.setWordWrap(True)
        hero_layout.addWidget(self.hero_purpose)

        hero_hint = QLabel("Listen for announcements and watch this screen for updates.")
        hero_hint.setObjectName("heroHint")
        hero_hint.setAlignment(Qt.AlignCenter)
        hero_hint.setWordWrap(True)
        hero_layout.addWidget(hero_hint)

        content_row.addWidget(self.hero_card, 3)

        right_col = QVBoxLayout()
        right_col.setSpacing(18)

        queue_card = QFrame()
        queue_card.setObjectName("queueCard")
        queue_layout = QVBoxLayout(queue_card)
        queue_layout.setContentsMargins(20, 18, 20, 20)
        queue_layout.setSpacing(10)

        queue_title = QLabel("Upcoming Queue")
        queue_title.setObjectName("panelTitle")
        queue_layout.addWidget(queue_title)

        queue_subtitle = QLabel("These are the next tickets expected to be called soon.")
        queue_subtitle.setObjectName("panelSubtitle")
        queue_subtitle.setWordWrap(True)
        queue_layout.addWidget(queue_subtitle)

        cards_grid = QGridLayout()
        cards_grid.setHorizontalSpacing(12)
        cards_grid.setVerticalSpacing(12)

        for index in range(6):
            card = TicketCard()
            self.ticket_cards.append(card)
            cards_grid.addWidget(card, index // 2, index % 2)

        queue_layout.addLayout(cards_grid)
        right_col.addWidget(queue_card, 3)

        stats_card = QFrame()
        stats_card.setObjectName("statsCard")
        stats_layout = QHBoxLayout(stats_card)
        stats_layout.setContentsMargins(20, 16, 20, 16)
        stats_layout.setSpacing(12)

        self.waiting_stat = self._build_stat_block("WAITING", "0", "Students in line")
        self.serving_stat = self._build_stat_block("IN SERVICE", "0", "Currently active tickets")
        self.total_served_stat = self._build_stat_block("TOTAL SERVED", "0", "Completed today")

        stats_layout.addWidget(self.waiting_stat)
        stats_layout.addWidget(self.serving_stat)
        stats_layout.addWidget(self.total_served_stat)

        right_col.addWidget(stats_card, 1)
        content_row.addLayout(right_col, 2)

        shell_layout.addLayout(content_row, 1)

    def _toggle_theme(self):
        self.theme_mode = "light" if self.theme_mode == "dark" else "dark"
        self._apply_theme()

    def _build_stat_block(self, label_text: str, value_text: str, helper_text: str) -> QWidget:
        block = QWidget()
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        value = QLabel(value_text)
        value.setObjectName("statValue")
        value.setAlignment(Qt.AlignCenter)

        label = QLabel(label_text)
        label.setObjectName("statLabel")
        label.setAlignment(Qt.AlignCenter)

        helper = QLabel(helper_text)
        helper.setObjectName("statHelper")
        helper.setAlignment(Qt.AlignCenter)
        helper.setWordWrap(True)

        layout.addWidget(value)
        layout.addWidget(label)
        layout.addWidget(helper)

        block.value_label = value
        return block

    def _setup_timers(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_display)
        self.refresh_timer.start(2000)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._toggle_pulse)
        self.pulse_timer.start(850)

    def _update_clock(self):
        now = datetime.now()
        self.clock_label.setText(now.strftime("%I:%M %p"))
        self.date_label.setText(now.strftime("%B %d, %Y"))

    def _toggle_pulse(self):
        self._pulse_on = not self._pulse_on
        self.hero_card.setProperty("pulse", self._pulse_on)
        self.style().unpolish(self.hero_card)
        self.style().polish(self.hero_card)

    def _refresh_display(self):
        try:
            waiting = self.db.get_waiting_queue()
            serving = self.db.get_currently_serving()
            stats = self.db.get_statistics()

            active_ticket = serving[0] if serving else None

            if active_ticket:
                counter_id = active_ticket.get("counter_id", 1)
                self.hero_ticket.setText(f"#{active_ticket['ticket_number']:04d}")
                purpose = active_ticket.get("purpose", "Student assistance")
                self.hero_purpose.setText(f"{purpose} (Counter {counter_id})")
            else:
                self.hero_ticket.setText("--")
                self.hero_purpose.setText("Waiting for the next ticket")

            for index, card in enumerate(self.ticket_cards, start=1):
                if index - 1 < len(waiting):
                    card.set_ticket(index, waiting[index - 1])
                else:
                    card.set_empty(index)

            self.waiting_stat.value_label.setText(str(len(waiting)))
            self.serving_stat.value_label.setText(str(len(serving)))
            self.total_served_stat.value_label.setText(str(stats.get("total_served", 0)))

        except Exception as error:
            print(f"Error refreshing live display monitor: {error}")

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


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = LiveDisplayMonitor()
    window.showFullScreen()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
