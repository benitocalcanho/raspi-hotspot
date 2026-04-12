from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.user import user_bp
from routes.gpio import gpio_bp
from routes.wifi import wifi_bp
from routes.calendar_sync import calendar_bp

__all__ = ["auth_bp", "admin_bp", "user_bp", "gpio_bp", "wifi_bp", "calendar_bp"]
