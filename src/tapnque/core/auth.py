"""
Authentication and local credential protection for TapNQue admin surfaces.
Credentials stored as salted SHA-256 hashes with constant-time verification.
"""

import hashlib
import hmac
import json
import secrets
from pathlib import Path
from typing import Dict, Optional

from tapnque.config import AUTH_FILE_PATH

DEFAULT_USERS = {
    "staff": {"username": "staff", "password": "staff123"},
    "super_admin": {"username": "admin", "password": "admin123"},
}


def _hash_password(password: str, salt: str) -> str:
    """Compute salted SHA-256 hash."""
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def _build_user(username: str, password: str) -> dict:
    """Construct user dictionary with new cryptographically random salt."""
    salt = secrets.token_hex(16)
    return {
        "username": username,
        "salt": salt,
        "password_hash": _hash_password(password, salt),
    }


def ensure_auth_file(file_path: Optional[Path] = None):
    """Create default credentials file if it does not exist."""
    target_path = Path(file_path).resolve() if file_path else AUTH_FILE_PATH
    if target_path.exists():
        return

    target_path.parent.mkdir(parents=True, exist_ok=True)
    users = {
        role: _build_user(credentials["username"], credentials["password"])
        for role, credentials in DEFAULT_USERS.items()
    }
    target_path.write_text(json.dumps(users, indent=2), encoding="utf-8")


def load_users(file_path: Optional[Path] = None) -> Dict[str, dict]:
    """Load credentials from JSON storage."""
    target_path = Path(file_path).resolve() if file_path else AUTH_FILE_PATH
    ensure_auth_file(target_path)
    try:
        return json.loads(target_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def authenticate(role: str, username: str, password: str, file_path: Optional[Path] = None) -> bool:
    """Verify role credentials using constant-time comparison."""
    user = load_users(file_path).get(role, {})
    expected_username = user.get("username", "")
    salt = user.get("salt", "")
    expected_hash = user.get("password_hash", "")

    if not expected_username or not salt or not expected_hash:
        return False

    password_hash = _hash_password(password, salt)
    return username == expected_username and hmac.compare_digest(password_hash, expected_hash)


try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
    )

    class AdminLoginDialog(QDialog):
        """Modal login dialog for staff and super admin screens."""

        def __init__(self, role: str, title: str, parent=None):
            super().__init__(parent)
            self.role = role
            self.setWindowTitle(title)
            self.setModal(True)
            self.setMinimumSize(430, 360)
            self._setup_ui(title)

        def _setup_ui(self, title: str):
            self.setStyleSheet(
                """
                QDialog {
                    background: #eef3ef;
                    color: #203126;
                    font-family: "Segoe UI";
                }
                QFrame#card {
                    background: #ffffff;
                    border: 1px solid #e3ebe3;
                    border-radius: 24px;
                }
                QLabel#title {
                    color: #18241b;
                    font-size: 28px;
                    font-weight: 800;
                }
                QLabel#subtitle {
                    color: #55665a;
                    font-size: 14px;
                }
                QLabel#fieldLabel {
                    color: #33483a;
                    font-size: 13px;
                    font-weight: 700;
                }
                QLineEdit {
                    background: #f7fbf8;
                    color: #172019;
                    border: 1px solid #d7e3d8;
                    border-radius: 14px;
                    padding: 13px 14px;
                    font-size: 15px;
                }
                QLineEdit:focus {
                    border: 2px solid #0b9b4a;
                }
                QPushButton#primaryButton {
                    background: #0a8c3c;
                    color: white;
                    border: none;
                    border-radius: 16px;
                    padding: 14px 20px;
                    font-size: 15px;
                    font-weight: 800;
                }
                QPushButton#primaryButton:hover {
                    background: #087632;
                }
                QPushButton#secondaryButton {
                    background: #edf2ee;
                    color: #294032;
                    border: none;
                    border-radius: 16px;
                    padding: 14px 20px;
                    font-size: 15px;
                    font-weight: 700;
                }
                QPushButton#secondaryButton:hover {
                    background: #e3ebe4;
                }
                """
            )

            root = QVBoxLayout(self)
            root.setContentsMargins(20, 20, 20, 20)

            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(28, 26, 28, 26)
            card_layout.setSpacing(14)

            title_label = QLabel(title)
            title_label.setObjectName("title")
            card_layout.addWidget(title_label)

            subtitle = QLabel("Sign in to continue.")
            subtitle.setObjectName("subtitle")
            card_layout.addWidget(subtitle)
            card_layout.addSpacing(10)

            username_label = QLabel("USERNAME")
            username_label.setObjectName("fieldLabel")
            card_layout.addWidget(username_label)

            self.username_input = QLineEdit()
            self.username_input.setPlaceholderText("Enter username")
            card_layout.addWidget(self.username_input)

            password_label = QLabel("PASSWORD")
            password_label.setObjectName("fieldLabel")
            card_layout.addWidget(password_label)

            self.password_input = QLineEdit()
            self.password_input.setPlaceholderText("Enter password")
            self.password_input.setEchoMode(QLineEdit.Password)
            self.password_input.returnPressed.connect(self._try_login)
            card_layout.addWidget(self.password_input)

            button_row = QHBoxLayout()
            button_row.setSpacing(12)
            button_row.addStretch()

            cancel_button = QPushButton("CANCEL")
            cancel_button.setObjectName("secondaryButton")
            cancel_button.clicked.connect(self.reject)
            button_row.addWidget(cancel_button)

            login_button = QPushButton("LOGIN")
            login_button.setObjectName("primaryButton")
            login_button.clicked.connect(self._try_login)
            button_row.addWidget(login_button)

            card_layout.addSpacing(8)
            card_layout.addLayout(button_row)
            root.addWidget(card)

            self.username_input.setFocus(Qt.OtherFocusReason)

        def _try_login(self):
            username = self.username_input.text().strip()
            password = self.password_input.text()

            if authenticate(self.role, username, password):
                self.accept()
                return

            QMessageBox.warning(self, "Login Failed", "Incorrect username or password.")
            self.password_input.clear()
            self.password_input.setFocus(Qt.OtherFocusReason)

    def require_admin_login(role: str, title: str, parent=None) -> bool:
        """Prompt admin authentication dialog."""
        ensure_auth_file()
        dialog = AdminLoginDialog(role, title, parent)
        return dialog.exec() == QDialog.Accepted

except ImportError:
    # PySide6 not installed in current environment
    AdminLoginDialog = None

    def require_admin_login(role: str, title: str, parent=None) -> bool:
        raise RuntimeError("PySide6 is required to display the login dialog.")
