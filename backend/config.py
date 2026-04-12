"""
Environment-based configuration.
All sensitive values must come from config/.env — never hardcoded.
"""
import os
from datetime import timedelta
from pathlib import Path

# Load .env from the config/ directory when running locally
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / "config" / ".env"
    load_dotenv(dotenv_path=env_file)
except ImportError:
    pass  # python-dotenv optional; rely on real env vars in production


class Config:
    # ── Flask ────────────────────────────────────────────────
    SECRET_KEY: str = os.environ["SECRET_KEY"]
    DEBUG: bool = os.getenv("FLASK_ENV", "production") == "development"

    # ── Database ─────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL", "sqlite:///data/raspi.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # ── JWT ──────────────────────────────────────────────────
    JWT_SECRET_KEY: str = os.environ["JWT_SECRET_KEY"]
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES: timedelta = timedelta(days=7)

    # ── CORS ─────────────────────────────────────────────────
    # In production limit to your actual origins
    CORS_ORIGINS: list = ["*"]

    # ── Admin bootstrap ──────────────────────────────────────
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.environ["ADMIN_PASSWORD"]
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@localhost")

    # ── Hotspot ──────────────────────────────────────────────
    HOTSPOT_SSID: str = os.getenv("HOTSPOT_SSID", "RaspiSetup")
    HOTSPOT_PASSPHRASE: str = os.getenv("HOTSPOT_PASSPHRASE", "raspisetup123")
    HOTSPOT_IP: str = os.getenv("HOTSPOT_IP", "192.168.50.1")
    HOTSPOT_DHCP_RANGE: str = os.getenv(
        "HOTSPOT_DHCP_RANGE", "192.168.50.10,192.168.50.50"
    )

    # ── ngrok ────────────────────────────────────────────────
    NGROK_AUTHTOKEN: str = os.getenv("NGROK_AUTHTOKEN", "")
    NGROK_STATIC_DOMAIN: str = os.getenv("NGROK_STATIC_DOMAIN", "")

    # ── Google Calendar ──────────────────────────────────────
    GOOGLE_CREDENTIALS_FILE: str = os.getenv("GOOGLE_CREDENTIALS_FILE", "")
    GOOGLE_TOKEN_FILE: str = os.getenv("GOOGLE_TOKEN_FILE", "")
    GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    CALENDAR_USER_CREATION_KEYWORD: str = os.getenv(
        "CALENDAR_USER_CREATION_KEYWORD", "CREATE_USER"
    )
    CALENDAR_SYNC_INTERVAL: int = int(os.getenv("CALENDAR_SYNC_INTERVAL", "300"))

    # ── GPIO ─────────────────────────────────────────────────
    GPIO_MODE: str = os.getenv("GPIO_MODE", "gpiozero")

    # ── Tailscale ────────────────────────────────────────────
    TAILSCALE_SUBNET: str = os.getenv("TAILSCALE_SUBNET", "100.64.0.0/10")

    # ── Application ──────────────────────────────────────────
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "5000"))
