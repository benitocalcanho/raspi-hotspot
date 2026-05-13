"""
Reed switch door sensor service.

The service is intentionally lazy: GPIO hardware is initialized from
create_app(), after Flask and the database are ready. This keeps route imports
safe on non-Pi machines and gives gpiozero callbacks a real app context.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from models import db
from models.door_log import DoorLog

logger = logging.getLogger(__name__)

DEFAULT_REED_GPIO = 23


class ReedSensorService:
    def __init__(self) -> None:
        self.app = None
        self.button = None
        self.pin_number = DEFAULT_REED_GPIO
        self.enabled = False
        self.error: Optional[str] = None
        self._last_logged_state: Optional[str] = None

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
            from gpiozero import Button, Device

            if os.getenv("GPIO_MODE", app.config.get("GPIO_MODE", "gpiozero")) != "gpiozero":
                from gpiozero.pins.mock import MockFactory

                Device.pin_factory = MockFactory()

            self.button = Button(self.pin_number, pull_up=True, bounce_time=0.2)
            self.button.when_pressed = self._handle_pressed
            self.button.when_released = self._handle_released
            self.enabled = True
            self.error = None
            initial_state = self.get_state()
            self._last_logged_state = initial_state if initial_state != "unknown" else None
            app.logger.info("Door reed sensor initialized on BCM%s.", self.pin_number)
        except Exception as exc:
            self.button = None
            self.enabled = False
            self.error = str(exc)
            app.logger.warning("Door reed sensor unavailable: %s", exc)

    def get_state(self) -> str:
        if not self.button:
            return "unknown"
        return self._state_from_pressed(bool(self.button.is_pressed))

    def status(self) -> dict:
        return {
            "state": self.get_state(),
            "enabled": self.enabled,
            "pin_number": self.pin_number,
            "error": self.error,
        }

    def _state_from_pressed(self, is_pressed: bool) -> str:
        # With pull_up=True and the switch wired to GND, gpiozero reports
        # pressed when the circuit is closed. The current wiring convention is
        # closed circuit = door open.
        return "open" if is_pressed else "closed"

    def _handle_pressed(self) -> None:
        self._log_state("open")

    def _handle_released(self) -> None:
        self._log_state("closed")

    def _log_state(self, state: str) -> None:
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
                    source="sensor",
                )
            )
            db.session.commit()
            self._last_logged_state = state


reed_sensor = ReedSensorService()
