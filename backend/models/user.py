"""
User model — stores credentials and role information.
"""
from datetime import datetime, timezone
import re
import bcrypt
from models import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")  # 'admin' | 'user'
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    # Source of account creation: 'manual' | 'calendar'
    created_by = db.Column(db.String(50), nullable=False, default="manual")
    # Optional reference to the Google Calendar event ID that created this user
    calendar_event_id = db.Column(db.String(200), nullable=True)

    audit_logs = db.relationship("AuditLog", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    @staticmethod
    def build_internal_email(username: str) -> str:
        """Generate a deterministic internal email placeholder from a username."""
        normalized = re.sub(r"[^a-z0-9._-]", "_", username.strip().lower())
        return f"{normalized}@local.user"

    def set_password(self, raw_password: str) -> None:
        if len(raw_password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        self.password_hash = bcrypt.hashpw(
            raw_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        return bcrypt.checkpw(
            raw_password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
        }

    def __repr__(self):
        return f"<User {self.username} [{self.role}]>"
