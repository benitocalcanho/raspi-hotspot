"""
Timezone utilities for deployment-local scheduling.

Goal: keep behavior plug-and-play across hosts without hardcoding a maintainer
timezone. The effective timezone is resolved from runtime configuration.
"""
import os
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # Python < 3.9
    from backports.zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app, has_app_context


def _valid_zone(name: str):
    if not name:
        return None
    try:
        ZoneInfo(name)
        return name
    except ZoneInfoNotFoundError:
        return None


def _system_timezone_name() -> str:
    # Debian/Raspbian commonly stores the timezone name here.
    tz_file = Path("/etc/timezone")
    if tz_file.exists():
        name = tz_file.read_text(encoding="utf-8").strip()
        valid = _valid_zone(name)
        if valid:
            return valid

    # If /etc/localtime is a symlink into zoneinfo, derive the name.
    localtime = Path("/etc/localtime")
    if localtime.exists() and localtime.is_symlink():
        resolved = str(localtime.resolve())
        marker = "/zoneinfo/"
        if marker in resolved:
            name = resolved.split(marker, 1)[1]
            valid = _valid_zone(name)
            if valid:
                return valid

    # Fall back to the current runtime tz object if it exposes a key.
    tzinfo = datetime.now().astimezone().tzinfo
    key = getattr(tzinfo, "key", None) or getattr(tzinfo, "zone", None)
    valid = _valid_zone(key or "")
    if valid:
        return valid

    return "UTC"


def get_effective_timezone_info(app=None):
    app_obj = app
    if app_obj is None and has_app_context():
        app_obj = current_app

    configured = ""
    if app_obj is not None:
        configured = (app_obj.config.get("APP_TIMEZONE") or "").strip()
    if configured:
        valid = _valid_zone(configured)
        if valid:
            return {"name": valid, "source": "config"}
        if app_obj is not None:
            app_obj.logger.warning("Invalid APP_TIMEZONE '%s'. Falling back to runtime detection.", configured)

    env_tz = (os.getenv("TZ") or "").strip()
    if env_tz:
        valid = _valid_zone(env_tz)
        if valid:
            return {"name": valid, "source": "env"}

    return {"name": _system_timezone_name(), "source": "system"}


def get_effective_timezone(app=None):
    info = get_effective_timezone_info(app=app)
    return ZoneInfo(info["name"])


def local_now(app=None):
    return datetime.now(get_effective_timezone(app=app))


def local_today(app=None):
    return local_now(app=app).date()
