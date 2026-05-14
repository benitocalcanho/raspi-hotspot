"""
Door reed sensor polling.

The reed switch is read through gpio_service so it shares the same GPIO
device cache and pin configuration path as the admin GPIO page.
"""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from models import db
from models.door_log import DoorLog

DEFAULT_REED_GPIO = 23


class ReedSensorService:
    def __init__(self) -> None:
        self.app = None
        self.pin_number = DEFAULT_REED_GPIO
        self.enabled = False
        self.error: Optional[str] = None
        self.active_state = "closed"
        self._last_logged_state: Optional[str] = None
        self._poll_thread: Optional[threading.Thread] = None

    def init_app(self, app) -> None:
        self.app = app
        self.pin_number = int(os.getenv("REED_GPIO", DEFAULT_REED_GPIO))
        self.active_state = os.getenv("REED_ACTIVE_STATE", "closed").strip().lower()
        if self.active_state not in ("open", "closed"):
            self.active_state = "closed"

        if not app.config.get("ENABLE_GPIO", False):
            self.enabled = False
            self.error = None
            app.logger.info("Door reed sensor disabled because ENABLE_GPIO=false.")
            return

        try:
            self._ensure_pin_configured()
            initial_state = self.get_state()
            self._last_logged_state = self._latest_logged_state() or initial_state
            self.enabled = initial_state != "unknown"
            self.error = None if self.enabled else self.error
            self._start_polling()
            app.logger.info("Door reed sensor polling GPIO%s.", self.pin_number)
        except Exception as exc:
            self.enabled = False
            self.error = str(exc)
            app.logger.warning("Door reed sensor unavailable: %s", exc)

    def get_state(self) -> str:
        try:
            from services.gpio_service import read_pin_state

            return self._state_from_active(bool(read_pin_state(self.pin_number)))
        except Exception as exc:
            self.error = str(exc)
            return "unknown"

    def status(self) -> dict:
        return {
            "state": self.get_state(),
            "enabled": self.enabled,
            "pin_number": self.pin_number,
            "error": self.error,
        }

    def _state_from_active(self, is_active: bool) -> str:
        if is_active:
            return self.active_state
        return "open" if self.active_state == "closed" else "closed"

    def poll_once(self, source: str = "sensor_poll") -> None:
        state = self.get_state()
        if state == "unknown":
            return
        self.enabled = True
        self.error = None
        self._log_state_if_changed(state, source)

    def _ensure_pin_configured(self) -> None:
        from services.gpio_service import configure_pin

        configure_pin(self.pin_number, "Door Sensor", "input")

    def _latest_logged_state(self) -> Optional[str]:
        latest = DoorLog.query.order_by(DoorLog.timestamp.desc()).first()
        return latest.state if latest else None

    def _log_state_if_changed(self, state: str, source: str) -> None:
        if state == self._last_logged_state:
            return
        db.session.add(
            DoorLog(
                timestamp=datetime.now(timezone.utc),
                state=state,
                source=source,
            )
        )
        db.session.commit()
        self._last_logged_state = state

    def _start_polling(self) -> None:
        if self._poll_thread and self._poll_thread.is_alive():
            return

        def poll() -> None:
            while True:
                time.sleep(1.0)
                if not self.app:
                    continue
                try:
                    with self.app.app_context():
                        self.poll_once()
                except Exception as exc:
                    self.error = str(exc)
                    self.app.logger.warning("Door reed sensor poll failed: %s", exc)
                finally:
                    db.session.remove()

        self._poll_thread = threading.Thread(target=poll, daemon=True)
        self._poll_thread.start()


reed_sensor = ReedSensorService()
