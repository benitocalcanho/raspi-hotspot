import os
try:
    import RPi.GPIO as GPIO
    PI_AVAILABLE = True
except ImportError:
    PI_AVAILABLE = False
from datetime import datetime
from models import db
from models.door_log import DoorLog

REED_GPIO = 23

class ReedSensor:
    def __init__(self):
        self.last_state = None
        if PI_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(REED_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(REED_GPIO, GPIO.BOTH, callback=self._handle_event, bouncetime=200)
            self.last_state = self._read_state()
        else:
            self.last_state = 'unknown'

    def _read_state(self):
        if not PI_AVAILABLE:
            return 'unknown'
        return 'closed' if GPIO.input(REED_GPIO) else 'open'

    def _handle_event(self, channel):
        state = self._read_state()
        if state != self.last_state:
            self.last_state = state
            db.session.add(DoorLog(timestamp=datetime.utcnow(), state=state, source='sensor'))
            db.session.commit()

    def get_state(self):
        return self._read_state()

reed_sensor = ReedSensor()
