"""
AuditLog model — records every authentication and sensitive event.
"""
import json
from datetime import datetime, timezone
from models import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    event = db.Column(db.String(80), nullable=False)   # e.g. 'login_success', 'login_failed'
    ip_address = db.Column(db.String(45), nullable=True)   # IPv4 or IPv6
    user_agent = db.Column(db.String(300), nullable=True)
    detail = db.Column(db.Text, nullable=True)             # JSON-serialisable extra info
    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),  # UTC
        index=True,
    )

    def to_dict(self) -> dict:
        parsed_detail = None
        if self.detail:
            try:
                parsed_detail = json.loads(self.detail)
            except (TypeError, ValueError):
                parsed_detail = {"raw": self.detail}

        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "event": self.event,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "detail": parsed_detail,
            "timestamp": self.timestamp.isoformat(),
        }

    def __repr__(self):
        return f"<AuditLog {self.event} user={self.user_id} at {self.timestamp}>"
