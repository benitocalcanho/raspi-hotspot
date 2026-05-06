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
        "DATABASE_URL", "sqlite:///instance/data/raspi.db"
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
    # All operational secrets (admin/cleaner credentials, WiFi, SMTP, etc.) are now managed via the dashboard and loaded from the database at runtime.

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

    # ── iCal Calendar ────────────────────────────────────────
    ICAL_URL: str = os.getenv("ICAL_URL", "")
    ICAL_GUEST_PASSWORD: str = os.getenv("ICAL_GUEST_PASSWORD", "")
    # Guest rotation schedule (HH:MM, 24h)
    CHECKOUT_TIME: str = os.getenv("CHECKOUT_TIME", "12:00")  # guests lose access
    CHECKIN_TIME: str = os.getenv("CHECKIN_TIME", "14:00")    # new guest account created
    CALENDAR_GUEST_DEFAULT_PASSWORD: str = os.getenv("CALENDAR_GUEST_DEFAULT_PASSWORD", "guest12345")
    CALENDAR_SYNC_ENABLED: bool = os.getenv("CALENDAR_SYNC_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")
    CALENDAR_SYNC_INTERVAL: int = int(os.getenv("CALENDAR_SYNC_INTERVAL", "300"))

    # ── GPIO ─────────────────────────────────────────────────
    GPIO_MODE: str = os.getenv("GPIO_MODE", "gpiozero")
    ENABLE_GPIO: bool = os.getenv("ENABLE_GPIO", "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    # ── Tailscale ────────────────────────────────────────────
    TAILSCALE_SUBNET: str = os.getenv("TAILSCALE_SUBNET", "100.64.0.0/10")
    ADMIN_REQUIRE_TAILSCALE: bool = os.getenv(
        "ADMIN_REQUIRE_TAILSCALE",
        "false",
    ).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    # ── Application ──────────────────────────────────────────
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "5000"))

    # ── Email/SMTP ────────────────────────────────────────────
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")
    EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "")
    EMAIL_RECIPIENT: str = os.getenv("EMAIL_RECIPIENT", "")
