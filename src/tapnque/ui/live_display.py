"""
Classic Live Display with Sound Notifications.
Public monitor showing "Now Serving" and "Waiting List" with sound effects.
"""

import sys
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tapnque.config import get_asset_path
from tapnque.core.database import get_database


class LiveDisplay(QWidget):
    """Large public monitor showing queue status with audio chime."""

    def __init__(self):
        super().__init__()
        self.db = get_database()
        self.last_serving = None
        self._setup_ui()
        self._setup_timer()
        self._load_sound()

    def _setup_ui(self):
        self.setWindowTitle("Queue Live Display")
        # 1024x700 fits 1366x768 Windows laptops even with the taskbar visible.
        self.setMinimumSize(1024, 700)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #0d1117;
            }
            QLabel {
                color: #ffffff;
            }
            QFrame {
                background-color: #161b22;
                border-radius: 15px;
            }
            QTableWidget {
                background-color: #161b22;
                color: #ffffff;
                border: none;
                gridline-color: #30363d;
            }
            QTableWidget::item {
                padding: 10px;
            }
            QHeaderView::section {
                background-color: #21262d;
                color: #8b949e;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
            """
        )

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("NOW SERVING")
        title.setFont(QFont("Arial", 48, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #58a6ff;")
        layout.addWidget(title)

        self.serving_frame = QFrame()
        self.serving_frame.setMinimumHeight(200)
        serving_layout = QVBoxLayout()

        serving_label = QLabel("CURRENT TICKET")
        serving_label.setFont(QFont("Arial", 18))
        serving_label.setStyleSheet("color: #8b949e;")
        serving_layout.addWidget(serving_label)

        self.ticket_display = QLabel("--")
        self.ticket_display.setFont(QFont("Consolas", 120, QFont.Bold))
        self.ticket_display.setAlignment(Qt.AlignCenter)
        self.ticket_display.setStyleSheet("color: #3fb950;")
        serving_layout.addWidget(self.ticket_display)

        self.counter_display = QLabel("Counter: --")
        self.counter_display.setFont(QFont("Arial", 24))
        self.counter_display.setAlignment(Qt.AlignCenter)
        self.counter_display.setStyleSheet("color: #f0883e;")
        serving_layout.addWidget(self.counter_display)

        self.serving_frame.setLayout(serving_layout)
        layout.addWidget(self.serving_frame)

        waiting_frame = QFrame()
        waiting_layout = QVBoxLayout()

        waiting_label = QLabel("WAITING LIST")
        waiting_label.setFont(QFont("Arial", 20, QFont.Bold))
        waiting_label.setStyleSheet("color: #8b949e;")
        waiting_layout.addWidget(waiting_label)

        self.waiting_table = QTableWidget()
        self.waiting_table.setColumnCount(4)
        self.waiting_table.setHorizontalHeaderLabels(["Ticket #", "Name", "Purpose", "Wait Time"])
        self.waiting_table.setFont(QFont("Arial", 14))
        self.waiting_table.verticalHeader().setDefaultSectionSize(40)
        self.waiting_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.waiting_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.waiting_table.setEditTriggers(QTableWidget.NoEditTriggers)

        waiting_layout.addWidget(self.waiting_table)
        waiting_frame.setLayout(waiting_layout)
        layout.addWidget(waiting_frame)

        stats_layout = QHBoxLayout()
        self.total_served_label = QLabel("Total Served: 0")
        self.total_served_label.setFont(QFont("Arial", 16))
        stats_layout.addWidget(self.total_served_label)

        self.avg_wait_label = QLabel("Avg Wait: 0 min")
        self.avg_wait_label.setFont(QFont("Arial", 16))
        stats_layout.addWidget(self.avg_wait_label)

        layout.addLayout(stats_layout)
        self.setLayout(layout)

    def _load_sound(self):
        self.sound_player = None
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

            sound_path = get_asset_path("notify.wav")
            if sound_path.exists():
                self.sound_player = QMediaPlayer()
                self.audio_output = QAudioOutput()
                self.sound_player.setAudioOutput(self.audio_output)
                self.sound_player.setSource(QUrl.fromLocalFile(str(sound_path)))
            else:
                self.sound_player = None
        except Exception as e:
            print(f"Sound initialization error: {e}")
            self.sound_player = None

    def _play_ding(self):
        if self.sound_player:
            try:
                self.sound_player.stop()
                self.sound_player.play()
            except Exception as e:
                print(f"Error playing sound: {e}")
        else:
            sys.stdout.write("\a")
            sys.stdout.flush()

    def _setup_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_display)
        self.refresh_timer.start(2000)
        self._refresh_display()

    def _refresh_display(self):
        try:
            serving = self.db.get_currently_serving()

            if serving:
                current = serving[0]
                ticket_num = current.get("ticket_number", 0)
                counter_id = current.get("counter_id", 1)

                self.ticket_display.setText(f"#{ticket_num:04d}")
                self.counter_display.setText(f"Counter: {counter_id}")

                if self.last_serving != ticket_num:
                    self._play_ding()
                    self.last_serving = ticket_num
            else:
                self.ticket_display.setText("--")
                self.counter_display.setText("Counter: --")
                self.last_serving = None

            waiting = self.db.get_waiting_queue()
            self.waiting_table.setRowCount(len(waiting))

            for row, ticket in enumerate(waiting):
                self.waiting_table.setItem(row, 0, QTableWidgetItem(f"#{ticket['ticket_number']:04d}"))
                self.waiting_table.setItem(row, 1, QTableWidgetItem(ticket.get("name", "")))
                self.waiting_table.setItem(row, 2, QTableWidgetItem(ticket.get("purpose", "")))

                try:
                    created = datetime.fromisoformat(ticket["created_at"])
                    wait_seconds = (datetime.now() - created).total_seconds()
                    wait_minutes = max(0, int(wait_seconds / 60))
                    self.waiting_table.setItem(row, 3, QTableWidgetItem(f"{wait_minutes} min"))
                except Exception:
                    self.waiting_table.setItem(row, 3, QTableWidgetItem("0 min"))

            stats = self.db.get_statistics()
            total = stats.get("total_served", 0)
            avg_wait = stats.get("average_wait_time", 0.0)

            self.total_served_label.setText(f"Total Served: {total}")
            self.avg_wait_label.setText(f"Avg Wait: {avg_wait/60:.1f} min")

        except Exception as e:
            print(f"Error refreshing display: {e}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = LiveDisplay()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
