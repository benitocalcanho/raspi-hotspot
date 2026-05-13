from datetime import datetime
from models import db
from models.door_log import DoorLog
import os

REED_GPIO = 23

try:
    from gpiozero import Button
    _use_mock = os.getenv("GPIO_MODE", "gpiozero") != "gpiozero"
    if _use_mock:
        from gpiozero.pins.mock import MockFactory
        from gpiozero import Device
        Device.pin_factory = MockFactory()
    button = Button(REED_GPIO, pull_up=True)
except ImportError:
    button = None

_last_logged_state = None

def _log_state(state: str):
    global _last_logged_state
    if state != _last_logged_state:
        db.session.add(DoorLog(timestamp=datetime.utcnow(), state=state, source="sensor"))
        db.session.commit()
        _last_logged_state = state

def _on_open():
    _log_state("open")

def _on_closed():
    _log_state("closed")

if button:
    button.when_pressed = _on_open   # circuit closes (LOW) when door opens
    button.when_released = _on_closed  # circuit opens (HIGH) when door closes

def get_state():
    if not button:
        return "unknown"
    return "open" if button.is_pressed else "closed"
