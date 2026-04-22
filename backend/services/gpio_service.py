"""
GPIO service — wraps gpiozero for safe use on Pi 3.
On non-Pi systems, gpiozero's MockFactory is used automatically.
"""
from __future__ import annotations

import os
from typing import Optional
from models import db
from models.gpio_pin import GpioPin

# Use mock pins when GPIO_MODE is not 'gpiozero' or when not running on Pi
_use_mock = os.getenv("GPIO_MODE", "gpiozero") != "gpiozero"

try:
    from gpiozero import LED, Button, Device
    if _use_mock:
        from gpiozero.pins.mock import MockFactory
        Device.pin_factory = MockFactory()
except ImportError:
    # Fallback: full mock when gpiozero is not installed (dev/CI environment)
    _use_mock = True


_pin_devices: dict[int, object] = {}   # BCM pin number → gpiozero device


def _get_or_create_device(pin_number: int, direction: str):
    """Return a cached gpiozero device for a given BCM pin."""
    if pin_number in _pin_devices:
        return _pin_devices[pin_number]

    if direction == "output":
        device = LED(pin_number)
    else:
        device = Button(pin_number)

    _pin_devices[pin_number] = device
    return device


def configure_pin(pin_number: int, label: str, direction: str) -> GpioPin:
    """Register a GPIO pin in the DB and prepare the hardware device."""
    if direction not in ("input", "output"):
        raise ValueError("direction must be 'input' or 'output'.")
    if pin_number < 2 or pin_number > 27:
        raise ValueError("BCM pin numbers must be between 2 and 27.")

    pin = GpioPin.query.filter_by(pin_number=pin_number).first()
    if not pin:
        pin = GpioPin(pin_number=pin_number, label=label, direction=direction)
        db.session.add(pin)
    else:
        pin.label = label
        pin.direction = direction
    db.session.commit()

    _get_or_create_device(pin_number, direction)
    return pin


def set_pin_state(pin_number: int, state: bool) -> GpioPin:
    """Activate or deactivate an output pin."""
    pin = GpioPin.query.filter_by(pin_number=pin_number).first()
    if not pin:
        raise LookupError(f"Pin BCM{pin_number} is not configured.")
    if pin.direction != "output":
        raise ValueError(f"Pin BCM{pin_number} is configured as input.")

    device = _get_or_create_device(pin_number, "output")
    if state:
        device.on()
    else:
        device.off()

    pin.state = state
    db.session.commit()
    return pin


def read_pin_state(pin_number: int) -> bool:
    """Read the current state of any configured pin."""
    pin = GpioPin.query.filter_by(pin_number=pin_number).first()
    if not pin:
        raise LookupError(f"Pin BCM{pin_number} is not configured.")

    device = _get_or_create_device(pin_number, pin.direction)

    if pin.direction == "output":
        live_state = bool(device.value)
    else:
        live_state = bool(device.is_pressed)

    if pin.state != live_state:
        pin.state = live_state
        db.session.commit()

    return live_state


def get_all_pins() -> list[GpioPin]:
    return GpioPin.query.all()


def delete_pin(pin_number: int) -> None:
    """Remove configuration and release the hardware pin."""
    pin = GpioPin.query.filter_by(pin_number=pin_number).first()
    if not pin:
        raise LookupError(f"Pin BCM{pin_number} is not configured.")

    device = _pin_devices.pop(pin_number, None)
    if device:
        device.close()

    db.session.delete(pin)
    db.session.commit()
