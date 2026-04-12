"""
Audit logging service — centralised helper used by every route that
needs to record user actions.
"""
import json
from datetime import datetime, timezone
from flask import request
from models import db
from models.audit_log import AuditLog


def log_event(
    event: str,
    user_id: int | None = None,
    detail: dict | None = None,
) -> AuditLog:
    """
    Persist an audit event.

    :param event:    Short event identifier, e.g. 'login_success', 'gpio_toggle'.
    :param user_id:  DB user ID (may be None for anonymous events like failed login).
    :param detail:   Optional dict of extra structured data (stored as JSON string).
    """
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.remote_addr

    entry = AuditLog(
        user_id=user_id,
        event=event,
        ip_address=ip,
        user_agent=request.headers.get("User-Agent", "")[:300],
        detail=json.dumps(detail) if detail else None,
        timestamp=datetime.now(timezone.utc),
    )
    db.session.add(entry)
    db.session.commit()
    return entry
