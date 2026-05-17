"""Guest access validity helpers."""
from __future__ import annotations

from datetime import date, time

from flask import current_app, has_app_context

from utils.timezone_utils import local_now


def _parse_hhmm(value: str, default: str = "12:00") -> time:
    try:
        h, m = (value or default).strip().split(":")
        return time(hour=int(h), minute=int(m))
    except Exception:
        h, m = default.split(":")
        return time(hour=int(h), minute=int(m))


def checkout_time_for_app(app) -> time:
    app_obj = app or (current_app if has_app_context() else None)
    try:
        from models.setting import Setting
        value = Setting.get("CHECKOUT_TIME") or (app_obj.config.get("CHECKOUT_TIME", "12:00") if app_obj else "12:00")
    except Exception:
        value = getattr(app_obj, "config", {}).get("CHECKOUT_TIME", "12:00")
    return _parse_hhmm(value, default="12:00")


def guest_stay_has_ended(valid_until: date | None, app=None) -> bool:
    """Return True only once the local checkout date/time has passed."""
    if valid_until is None:
        return False
    now = local_now(app=app)
    if now.date() > valid_until:
        return True
    if now.date() < valid_until:
        return False
    return now.time() >= checkout_time_for_app(app)
