from datetime import datetime
from . import db

class DoorLog(db.Model):
    __tablename__ = 'door_log'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    state = db.Column(db.String(10), nullable=False)  # 'open' or 'closed'
    source = db.Column(db.String(32), nullable=True)  # e.g., 'sensor'
