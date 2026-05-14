"""
DoorLog model — records reed switch open/closed changes.
"""
from datetime import datetime, timezone
from models import db


class DoorLog(db.Model):
    __tablename__ = "door_logs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    state = db.Column(db.String(16), nullable=False)
    source = db.Column(db.String(40), nullable=False, default="sensor")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "state": self.state,
            "source": self.source,
        }
