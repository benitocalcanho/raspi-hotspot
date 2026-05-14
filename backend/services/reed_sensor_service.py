"""
Reed switch door sensor service.

The service polls GPIO23 through gpio_service, so it uses the same hardware
path as the existing GPIO admin page and does not claim the pin separately.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from models import db
from models.door_log import DoorLog

logger = logging.getLogger(__name__)

DEFAULT_REED_GPIO = 23


class ReedSensorService:
    def __init__(self) -> None:
        self.app = None
        self.pin_number = DEFAULT_REED_GPIO
        self.enabled = False
        self.error: Optional[str] = None
        self._last_logged_state: Optional[str] = None
        self._poll_thread = None

    def init_app(self, app) -> None:
        """Initialize GPIO monitoring if the deployment enables GPIO."""
        self.app = app
        self.pin_number = int(os.getenv("REED_GPIO", DEFAULT_REED_GPIO))

        if not app.config.get("ENABLE_GPIO", False):
            self.enabled = False
            self.error = None
            app.logger.info("Door reed sensor disabled because ENABLE_GPIO=false.")
            return

        try:
            self._ensure_pin_configured()
            initial_state = self.get_state()
            self._last_logged_state = initial_state if initial_state != "unknown" else None
            self.enabled = True
            self.error = None
            self._start_polling()
            app.logger.info("Door reed sensor polling GPIO%s.", self.pin_number)
        except Exception as exc:
            self.enabled = False
            self.error = str(exc)
            app.logger.warning("Door reed sensor unavailable: %s", exc)

    def get_state(self) -> str:
        try:
            from services.gpio_service import read_pin_state

            return self._state_from_pressed(bool(read_pin_state(self.pin_number)))
        except Exception as exc:
            self.error = str(exc)
            return "unknown"

    def status(self) -> dict:
        self.sync_current_state(source="sensor_status")
        return {
            "state": self.get_state(),
            "enabled": self.enabled,
            "pin_number": self.pin_number,
            "error": self.error,
        }

    def sync_current_state(self, source: str = "sensor_poll") -> None:
        """Log the current state if it changed since the last recorded state."""
        state = self.get_state()
        if state != "unknown":
            self._log_state(state, source=source)

    def _state_from_pressed(self, is_pressed: bool) -> str:
        # The GPIO admin page reports True when the input is active. Current
        # wiring convention: active input = door open.
        return "open" if is_pressed else "closed"

    def _log_state(self, state: str, source: str = "sensor") -> None:
        if state == self._last_logged_state:
            return
        if not self.app:
            logger.warning("Door sensor event ignored because app is not initialized.")
            return

        with self.app.app_context():
            db.session.add(
                DoorLog(
                    timestamp=datetime.now(timezone.utc),
                    state=state,
                    source=source,
                )
            )
            db.session.commit()
            self._last_logged_state = state

    def _ensure_pin_configured(self) -> None:
        from models.gpio_pin import GpioPin
        from services.gpio_service import configure_pin

        pin = GpioPin.query.filter_by(pin_number=self.pin_number).first()
        if not pin:
            configure_pin(self.pin_number, "Door Sensor", "input")
        elif pin.direction != "input":
            raise ValueError(f"GPIO{self.pin_number} is configured as {pin.direction}, expected input.")

    def _start_polling(self) -> None:
        if self._poll_thread and self._poll_thread.is_alive():
            return

        def poll() -> None:
            while True:
                time.sleep(1.0)
                if not self.enabled:
                    continue
                try:
                    self.sync_current_state(source="sensor_poll")
                except Exception as exc:
                    logger.warning("Door reed sensor poll failed: %s", exc)

        self._poll_thread = threading.Thread(target=poll, daemon=True)
        self._poll_thread.start()


reed_sensor = ReedSensorService()
