"""
GpioPin model — stores the configured GPIO pins and their current state.
"""
from datetime import datetime, timezone
from models import db


class GpioPin(db.Model):
    __tablename__ = "gpio_pins"

    id = db.Column(db.Integer, primary_key=True)
    pin_number = db.Column(db.Integer, unique=True, nullable=False)   # BCM pin number
    label = db.Column(db.String(80), nullable=False, default="")      # Human-readable name
    direction = db.Column(db.String(10), nullable=False, default="output")  # 'input' | 'output'
    state = db.Column(db.Boolean, nullable=False, default=False)      # current logical state
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pin_number": self.pin_number,
            "label": self.label,
            "direction": self.direction,
            "state": self.state,
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self):
        return f"<GpioPin BCM{self.pin_number} '{self.label}' state={self.state}>"
