"""
GPIO service — wraps gpiozero for safe use on Pi 3.
On non-Pi systems, gpiozero's MockFactory is used automatically.
"""
from __future__ import annotations

import os
import threading
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
    LED = Button = Device = None
    _use_mock = True

try:
    import lgpio
except ImportError:
    lgpio = None


_pin_devices: dict[int, object] = {}   # BCM pin number → gpiozero device
_pin_directions: dict[int, str] = {}
_input_read_lock = threading.Lock()


def _get_or_create_device(pin_number: int, direction: str):
    """Return a cached gpiozero device for a given BCM pin."""
    if LED is None or Button is None:
        raise RuntimeError("gpiozero is not installed; GPIO hardware is unavailable.")

    if pin_number in _pin_devices:
        if _pin_directions.get(pin_number) == direction:
            return _pin_devices[pin_number]
        old_device = _pin_devices.pop(pin_number)
        _pin_directions.pop(pin_number, None)
        old_device.close()

    if direction == "output":
        # active_high=False: most relay boards are active-LOW (LOW = relay ON)
        # initial_value=False: start inactive (pin HIGH = relay OFF)
        device = LED(pin_number, active_high=False, initial_value=False)
    else:
        # Prefer direct lgpio reads for inputs on Pi. Long-lived gpiozero Button
        # instances can report stale input state on some Pi 2 / Bookworm-Trixie
        # combinations when used from inside Docker.
        if lgpio is not None and not _use_mock:
            _pin_directions[pin_number] = direction
            return None
        device = Button(pin_number, pull_up=True, bounce_time=0.2)

    _pin_devices[pin_number] = device
    _pin_directions[pin_number] = direction
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


def _read_input_pin_state(pin_number: int) -> bool:
    """Read an input pin as active-low with an internal pull-up."""
    if lgpio is not None and not _use_mock:
        with _input_read_lock:
            handle = lgpio.gpiochip_open(0)
            try:
                lgpio.gpio_claim_input(handle, pin_number, lgpio.SET_PULL_UP)
                # Reed switch wiring uses pull-up: closed switch pulls GPIO LOW.
                return not bool(lgpio.gpio_read(handle, pin_number))
            finally:
                try:
                    lgpio.gpio_free(handle, pin_number)
                finally:
                    lgpio.gpiochip_close(handle)

    device = _get_or_create_device(pin_number, "input")
    return bool(device.is_pressed)


def read_pin_state(pin_number: int) -> bool:
    """Read the current state of any configured pin."""
    pin = GpioPin.query.filter_by(pin_number=pin_number).first()
    if not pin:
        raise LookupError(f"Pin BCM{pin_number} is not configured.")

    if pin.direction == "output":
        device = _get_or_create_device(pin_number, "output")
        live_state = bool(device.value)
    else:
        live_state = _read_input_pin_state(pin_number)

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
    _pin_directions.pop(pin_number, None)
    if device:
        device.close()

    db.session.delete(pin)
    db.session.commit()
