"""
Flask application factory.
"""
import time
import datetime
print("System time:", datetime.datetime.now())
print("TZ name:", time.tzname)
print("TZ offset (seconds):", -time.timezone)

# Set logging to use system local time for timestamps
import logging
import time

class LocalTimezoneFormatter(logging.Formatter):
    converter = time.localtime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s in %(module)s: %(message)s",
)
for handler in logging.root.handlers:
    handler.setFormatter(LocalTimezoneFormatter(handler.formatter._fmt))
import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config import Config
from models import db
from models.user import User
from models.setting import Setting
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.user import user_bp
from routes.wifi import wifi_bp
from routes.calendar_sync import calendar_bp
from routes.uploads import uploads_bp


def create_app(config_class=Config):
    # Serve the pre-built Vue SPA from frontend/dist/
    static_folder = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
    app = Flask(__name__, static_folder=static_folder, static_url_path="")

    app.config.from_object(config_class)

    # Extensions
    db.init_app(app)
    JWTManager(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    # Blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    if app.config.get("ENABLE_GPIO", False):
        from routes.gpio import gpio_bp

        app.register_blueprint(gpio_bp, url_prefix="/api/gpio")
    app.register_blueprint(wifi_bp, url_prefix="/api/wifi")
    app.register_blueprint(calendar_bp, url_prefix="/api/calendar")
    app.register_blueprint(uploads_bp, url_prefix="/api/uploads")


    # Create DB tables and seed admin user on first run
    with app.app_context():
        db.create_all()       # creates settings table first
        _migrate_add_valid_until(app)  # must run before any ORM queries
        _load_db_settings(app)
        _seed_admin(app)
        _seed_gpio(app)
        _migrate_calendar_users_to_guest(app)

        # Stop any running ngrok tunnels/processes before starting a new tunnel
        try:
            import subprocess
            subprocess.run([
                "bash",
                os.path.join(os.path.dirname(__file__), "..", "scripts", "stop_ngrok.sh")
            ], check=False)
        except Exception as exc:
            app.logger.warning(f"Failed to run stop_ngrok.sh: {exc}")

        # Start ngrok tunnel if authtoken is set
        try:
            from services import ngrok_service
            port = int(app.config.get("APP_PORT", 5000))
            authtoken = app.config.get("NGROK_AUTHTOKEN", "")
            if authtoken:
                ngrok_service.start_tunnel(port=port)
                app.logger.info("ngrok tunnel started automatically on app startup.")
            else:
                app.logger.info("ngrok authtoken not set; tunnel not started.")
        except Exception as exc:
            app.logger.error(f"Failed to start ngrok tunnel on startup: {exc}")

        # Background watchdog: restart ngrok tunnel if it drops (e.g. after WiFi switch)
        _start_ngrok_watchdog(app)

    if app.config.get("CALENDAR_SYNC_ENABLED", True):
        should_start_scheduler = (not app.debug) or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
        if should_start_scheduler:
            from services.calendar_service import start_scheduler

            start_scheduler(app)

    # Serve Vue SPA for all non-API routes (client-side routing)
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path):
        dist_dir = app.static_folder
        file_path = os.path.join(dist_dir, path)
        if path and os.path.exists(file_path):
            return send_from_directory(dist_dir, path)
        return _spa_index(app)

    # Flask's static file handler (static_url_path="") can intercept Vue Router
    # paths like /guest before the catch-all above runs, returning 404.
    # This handler catches those and falls back to the SPA entry point.
    @app.errorhandler(404)
    def handle_404(e):
        # Only fall back for non-API requests
        from flask import request
        if request.path.startswith("/api/"):
            return e
        return _spa_index(app)

    return app


def _start_ngrok_watchdog(app):
    """Start a background thread that restarts the ngrok tunnel if it drops."""
    import threading

    def watchdog():
        while True:
            time.sleep(60)
            try:
                with app.app_context():
                    authtoken = app.config.get("NGROK_AUTHTOKEN", "")
                    if not authtoken:
                        continue
                    from services import ngrok_service
                    port = int(app.config.get("APP_PORT", 5000))
                    if not ngrok_service._is_tunnel_alive():
                        app.logger.info("ngrok watchdog: tunnel dead, restarting...")
                        ngrok_service.start_tunnel(port=port)
            except Exception as exc:
                app.logger.warning(f"ngrok watchdog error: {exc}")

    t = threading.Thread(target=watchdog, daemon=True)
    t.start()


def _spa_index(app):
    from flask import send_from_directory
    response = send_from_directory(app.static_folder, "index.html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _load_db_settings(app):
    """Load persisted settings from the DB into app.config, overriding env vars.
    Called once at startup so services pick up GUI-saved values immediately.
    """
    for row in Setting.query.all():
        if row.value:
            app.config[row.key] = row.value
    app.logger.debug("DB settings loaded into app.config.")


def _seed_admin(app):
    """Create the bootstrap admin account if it doesn't exist."""
    from models.user import User
    from models.setting import Setting

    admin_username = Setting.get("ADMIN_USERNAME") or "admin"
    admin_password = Setting.get("ADMIN_PASSWORD") or "admin12345"
    existing = User.query.filter_by(username=admin_username).first()
    if not existing:
        admin = User(
            username=admin_username,
            email=User.build_internal_email(admin_username),
            role="admin",
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        app.logger.info("Bootstrap admin account created.")


def _seed_gpio(app):
    """Create default relay pins on first install if none exist."""
    from models.gpio_pin import GpioPin
    if GpioPin.query.count() == 0:
        defaults = [
            GpioPin(pin_number=17, label="Street Door", direction="output", state=False),
            GpioPin(pin_number=27, label="Apartment Door", direction="output", state=False),
        ]
        db.session.add_all(defaults)
        db.session.commit()
        app.logger.info("Default GPIO relay pins seeded.")


def _migrate_calendar_users_to_guest(app):
    """Ensure historical calendar-created accounts use guest role."""
    updated = (
        User.query
        .filter(User.created_by == "calendar", User.role == "user")
        .update({"role": "guest"}, synchronize_session=False)
    )
    if updated:
        db.session.commit()
        app.logger.info("Migrated %d calendar user(s) to guest role.", updated)


def _migrate_add_valid_until(app):
    """Add valid_until column to users table if it doesn't exist (SQLite migration)."""
    from sqlalchemy import inspect, text
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [c["name"] for c in inspector.get_columns("users")]
        if "valid_until" not in columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN valid_until DATE"))
            db.session.commit()
            app.logger.info("Migration: added valid_until column to users table.")


if __name__ == "__main__":
    app = create_app()
    # Store app globally for background threads
    import flask
    flask.current_app = app
    app.run(
        host=app.config["APP_HOST"],
        port=app.config["APP_PORT"],
        debug=app.config["DEBUG"],
    )
