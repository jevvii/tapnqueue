"""
Main Launcher for TapNQue Student Kiosk Ticketing System.
Provides a central portal to launch all system modules.
"""

import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MainLauncher(QWidget):
    """Main launcher hub to open different system modules."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎓 TapNQue - Student Kiosk Ticketing System")
        self.setMinimumSize(600, 520)
        self.open_windows = []
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(
            """
            QWidget {
                background-color: #1a1a2e;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #16213e;
                color: #ffffff;
                border: 2px solid #0f3460;
                border-radius: 14px;
                padding: 18px 20px;
                font-size: 15px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #0f3460;
                border: 2px solid #e94560;
            }
            """
        )

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(40, 36, 40, 36)

        title = QLabel("🎓 TAPNQUE QUEUE SYSTEM")
        title.setFont(QFont("Arial", 26, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #e94560;")
        layout.addWidget(title)

        subtitle = QLabel("Select a station to launch:")
        subtitle.setFont(QFont("Arial", 13))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #a0a0a0;")
        layout.addWidget(subtitle)

        layout.addSpacing(14)

        kiosk_btn = self._create_module_button(
            "🎟️", "Student Kiosk Registration",
            "Self-service touch screen for student ticket creation",
            self._open_student_kiosk,
        )
        layout.addWidget(kiosk_btn)

        live_btn = self._create_module_button(
            "📺", "Live Display Monitor",
            "TV-optimized waiting area monitor showing active & upcoming queue",
            self._open_live_display,
        )
        layout.addWidget(live_btn)

        staff_btn = self._create_module_button(
            "💼", "Staff Service Desk",
            "Counter staff portal to call, recall, and complete student requests",
            self._open_staff_admin,
        )
        layout.addWidget(staff_btn)

        admin_btn = self._create_module_button(
            "🔧", "Super Admin Console",
            "Operational metrics, queue monitoring, and system configuration",
            self._open_super_admin,
        )
        layout.addWidget(admin_btn)

        layout.addSpacing(10)

        info = QLabel("💡 Tip: You can launch multiple stations simultaneously on one or more monitors.")
        info.setFont(QFont("Arial", 10))
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("color: #7b889b;")
        layout.addWidget(info)

        self.setLayout(layout)

    def _create_module_button(self, icon: str, title: str, description: str, callback) -> QPushButton:
        btn = QPushButton()
        btn.setMinimumHeight(76)
        btn.setText(f"{icon}  {title}\n    {description}")
        btn.setFont(QFont("Arial", 12))
        btn.clicked.connect(callback)
        return btn

    def _open_student_kiosk(self):
        from tapnque.ui.kiosk import StudentKiosk, LoadingScreen

        kiosk_window = StudentKiosk()
        loading = LoadingScreen(kiosk_window)
        loading.show()
        self.open_windows.append(kiosk_window)
        self.open_windows.append(loading)

    def _open_live_display(self):
        from tapnque.ui.monitor import LiveDisplayMonitor

        live_window = LiveDisplayMonitor()
        live_window.show()
        self.open_windows.append(live_window)

    def _open_staff_admin(self):
        from tapnque.ui.staff import StaffAdmin

        staff_window = StaffAdmin()
        if not getattr(staff_window, "authenticated", False):
            return
        staff_window.show()
        self.open_windows.append(staff_window)

    def _open_super_admin(self):
        from tapnque.ui.super_admin import SuperAdmin

        admin_window = SuperAdmin()
        if not getattr(admin_window, "authenticated", False):
            return
        admin_window.show()
        self.open_windows.append(admin_window)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainLauncher()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
