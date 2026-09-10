"""
TapNQue Configuration Module
Centralizes paths, settings, and environment variables.
"""

import os
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent

# Directory locations with environment override support
DATA_DIR = Path(os.getenv("TAPNQUE_DATA_DIR", PROJECT_ROOT / "data")).resolve()
ASSETS_DIR = Path(os.getenv("TAPNQUE_ASSETS_DIR", PROJECT_ROOT / "assets")).resolve()
IMAGES_DIR = ASSETS_DIR / "images"
AUDIO_DIR = ASSETS_DIR / "audio"
DOCS_DIR = PROJECT_ROOT / "docs"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database & Credentials file paths
DB_PATH = Path(os.getenv("TAPNQUE_DB_PATH", DATA_DIR / "kiosk.db")).resolve()
AUTH_FILE_PATH = Path(os.getenv("TAPNQUE_AUTH_PATH", DATA_DIR / "admin_users.json")).resolve()
LEGACY_JSON_PATH = Path(os.getenv("TAPNQUE_LEGACY_JSON", DATA_DIR / "queue_db.json")).resolve()

# SMTP & Notification Settings
SMTP_SERVER = os.getenv("TAPNQUE_SMTP_SERVER", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("TAPNQUE_SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("TAPNQUE_SENDER_EMAIL", "").strip()
SENDER_PASSWORD = os.getenv("TAPNQUE_SENDER_PASSWORD", "").strip()

# SMS Gateway & Capstone Simulation Settings
SMS_GATEWAY_URL = os.getenv("TAPNQUE_SMS_GATEWAY_URL", "https://api.semaphore.co/api/v4/messages").strip()
DEFAULT_SMS_ENABLED = os.getenv("TAPNQUE_SMS_ENABLED", "1").strip().lower() in ("1", "true", "yes")
DEFAULT_SMS_MOCK_MODE = os.getenv("TAPNQUE_SMS_MOCK_MODE", "1").strip().lower() in ("1", "true", "yes")
DEFAULT_SMS_API_KEY = os.getenv("TAPNQUE_SMS_API_KEY", "").strip()
DEFAULT_SMS_SENDER_NAME = os.getenv("TAPNQUE_SMS_SENDER_NAME", "TapNQue").strip()

# Telegram Bot & QR Code Notification Settings
TELEGRAM_BOT_TOKEN = os.getenv("TAPNQUE_TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_BOT_USERNAME = os.getenv("TAPNQUE_TELEGRAM_BOT_USERNAME", "").strip().lstrip("@")
DEFAULT_TELEGRAM_ENABLED = os.getenv("TAPNQUE_TELEGRAM_ENABLED", "1").strip().lower() in ("1", "true", "yes")
DEFAULT_TELEGRAM_MOCK_MODE = os.getenv("TAPNQUE_TELEGRAM_MOCK_MODE", "1").strip().lower() in ("1", "true", "yes")


def get_asset_path(filename: str) -> Path:
    """
    Search for an asset across candidate locations:
    1. assets/images/
    2. assets/audio/
    3. assets/
    4. PROJECT_ROOT/ (fallback for legacy layouts)
    """
    candidates = [
        IMAGES_DIR / filename,
        AUDIO_DIR / filename,
        ASSETS_DIR / filename,
        PROJECT_ROOT / filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    # Default fallback even if file does not yet exist
    return (IMAGES_DIR / filename).resolve()
