"""
GpioPin model — stores the configured GPIO pins and their current state.
Fields:
    id: Primary key
    pin_number: BCM pin number (unique)
    label: Human-readable name for the pin
    direction: 'input' or 'output'
    state: Current logical state (True/False)
    updated_at: UTC timestamp of last update
"""
from datetime import datetime, timezone
from models import db
from utils.datetime_utils import utc_isoformat


class GpioPin(db.Model):
    __tablename__ = "gpio_pins"

    id = db.Column(db.Integer, primary_key=True)
    pin_number = db.Column(db.Integer, unique=True, nullable=False)   # BCM pin number (unique)
    label = db.Column(db.String(80), nullable=False, default="")      # Human-readable name for the pin
    direction = db.Column(db.String(10), nullable=False, default="output")  # Pin direction: 'input' or 'output'
    state = db.Column(db.Boolean, nullable=False, default=False)      # Current logical state (True/False)
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
            "updated_at": utc_isoformat(self.updated_at),
        }

    def __repr__(self):
        return f"<GpioPin BCM{self.pin_number} '{self.label}' state={self.state}>"
