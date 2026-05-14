"""
Automatic log retention cleanup.

Keeps the SQLite database from growing forever on small Raspberry Pi SD cards.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone

from models import db
from models.audit_log import AuditLog
from models.door_log import DoorLog

_started = False


def cleanup_logs(app) -> dict:
    """Delete audit and door log rows older than the configured retention windows."""
    audit_days = int(app.config.get("AUDIT_LOG_RETENTION_DAYS", 180))
    door_days = int(app.config.get("DOOR_LOG_RETENTION_DAYS", 90))
    now = datetime.now(timezone.utc)

    audit_deleted = (
        AuditLog.query
        .filter(AuditLog.timestamp < now - timedelta(days=audit_days))
        .delete(synchronize_session=False)
    )
    door_deleted = (
        DoorLog.query
        .filter(DoorLog.timestamp < now - timedelta(days=door_days))
        .delete(synchronize_session=False)
    )

    if audit_deleted or door_deleted:
        db.session.commit()
        app.logger.info(
            "Log retention cleanup deleted %s audit row(s) and %s door row(s).",
            audit_deleted,
            door_deleted,
        )
    else:
        db.session.rollback()

    return {"audit_deleted": audit_deleted, "door_deleted": door_deleted}


def start_retention_cleanup(app) -> None:
    """Run cleanup once at startup, then every 24 hours."""
    global _started
    if _started:
        return
    _started = True

    def worker() -> None:
        while True:
            try:
                with app.app_context():
                    cleanup_logs(app)
            except Exception as exc:
                app.logger.warning("Log retention cleanup failed: %s", exc)
            time.sleep(24 * 60 * 60)

    threading.Thread(target=worker, daemon=True).start()
