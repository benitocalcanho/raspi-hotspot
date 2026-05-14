from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import all models so db.create_all() sees them
from .user import User
from .setting import Setting
from .audit_log import AuditLog
from .gpio_pin import GpioPin
