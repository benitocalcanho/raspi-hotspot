"""
App settings — persisted key/value store so secrets can be managed via the
admin GUI instead of editing .env files directly.
Fields:
    key: Setting key (unique, primary key)
    value: Setting value (string)
    updated_at: UTC timestamp of last update
Values stored here override the corresponding environment variables at runtime.
"""
from datetime import datetime, timezone
from models import db


class Setting(db.Model):
    __tablename__ = "settings"

    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    @classmethod
    def get(cls, key: str, default=None):
        """Return the stored value for key, or default if not found."""
        row = cls.query.filter_by(key=key).first()
        return row.value if row is not None else default

    @classmethod
    def set(cls, key: str, value: str) -> None:
        """Insert or update a setting value."""
        row = cls.query.filter_by(key=key).first()
        if row:
            row.value = value
            row.updated_at = datetime.now(timezone.utc)
        else:
            db.session.add(cls(key=key, value=value))
        db.session.commit()

    def __repr__(self):
        return f"<Setting {self.key}>"
