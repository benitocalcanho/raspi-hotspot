"""
Audit logging service — centralised helper used by every route that
needs to record user actions.
"""
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from flask import request, has_request_context
from models import db
from models.audit_log import AuditLog


def _detect_browser(user_agent: str) -> str:
    ua = user_agent.lower()
    if "edg/" in ua:
        return "Edge"
    if "opr/" in ua or "opera" in ua:
        return "Opera"
    if "chrome/" in ua and "edg/" not in ua:
        return "Chrome"
    if "firefox/" in ua:
        return "Firefox"
    if "safari/" in ua and "chrome/" not in ua:
        return "Safari"
    return "Unknown"


def _detect_device(user_agent: str) -> str:
    ua = user_agent.lower()
    if "iphone" in ua:
        return "iPhone"
    if "ipad" in ua:
        return "iPad"
    if "android" in ua and "mobile" in ua:
        return "Android Phone"
    if "android" in ua:
        return "Android Device"
    if "windows" in ua or "macintosh" in ua or "linux" in ua:
        return "Desktop"
    return "Unknown"


def _detect_os(user_agent: str) -> str:
    ua = user_agent.lower()
    if "windows" in ua:
        return "Windows"
    if "android" in ua:
        return "Android"
    if "iphone" in ua or "ipad" in ua or "ios" in ua:
        return "iOS"
    if "mac os x" in ua or "macintosh" in ua:
        return "macOS"
    if "linux" in ua:
        return "Linux"
    return "Unknown"


def _detect_language(accept_language: str) -> str:
    first = accept_language.split(",")[0].strip()
    return first[:32] if first else "Unknown"


def _request_metadata() -> Dict[str, Any]:
    if not has_request_context():
        return {"ip": None, "user_agent": "", "client": {}}

    forwarded_for = request.headers.get("X-Forwarded-For", "")
    forwarded_ip = forwarded_for.split(",")[0].strip() if forwarded_for else ""
    ip = forwarded_ip or request.headers.get("X-Real-IP", "") or request.remote_addr
    user_agent = request.headers.get("User-Agent", "")[:300]
    accept_language = request.headers.get("Accept-Language", "")

    client = {
        "browser": _detect_browser(user_agent),
        "device": _detect_device(user_agent),
        "os": _detect_os(user_agent),
        "language": _detect_language(accept_language),
        "path": request.path,
        "method": request.method,
    }
    return {"ip": ip, "user_agent": user_agent, "client": client}


def log_event(
    event: str,
    user_id: Optional[int] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Persist an audit event.

    :param event:    Short event identifier, e.g. 'login_success', 'gpio_toggle'.
    :param user_id:  DB user ID (may be None for anonymous events like failed login).
    :param detail:   Optional dict of extra structured data (stored as JSON string).
    """
    meta = _request_metadata()
    merged_detail = dict(detail) if detail else {}
    merged_detail["client"] = meta["client"]

    entry = AuditLog(
        user_id=user_id,
        event=event,
        ip_address=meta["ip"],
        user_agent=meta["user_agent"],
        detail=json.dumps(merged_detail),
        timestamp=datetime.now(timezone.utc),
    )
    db.session.add(entry)
    db.session.commit()
    return entry
