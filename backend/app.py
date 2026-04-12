"""
Flask application factory.
"""
import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config import Config
from models import db
from models.user import User
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.user import user_bp
from routes.gpio import gpio_bp
from routes.wifi import wifi_bp
from routes.calendar_sync import calendar_bp


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
    app.register_blueprint(gpio_bp, url_prefix="/api/gpio")
    app.register_blueprint(wifi_bp, url_prefix="/api/wifi")
    app.register_blueprint(calendar_bp, url_prefix="/api/calendar")

    # Create DB tables and seed admin user on first run
    with app.app_context():
        db.create_all()
        _seed_admin(app)

    # Serve Vue SPA for all non-API routes (client-side routing)
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path):
        dist_dir = app.static_folder
        file_path = os.path.join(dist_dir, path)
        if path and os.path.exists(file_path):
            return send_from_directory(dist_dir, path)
        return send_from_directory(dist_dir, "index.html")

    return app


def _seed_admin(app):
    """Create the bootstrap admin account if it doesn't exist."""
    from models.user import User

    cfg = app.config
    existing = User.query.filter_by(username=cfg["ADMIN_USERNAME"]).first()
    if not existing:
        admin = User(
            username=cfg["ADMIN_USERNAME"],
            email=cfg["ADMIN_EMAIL"],
            role="admin",
        )
        admin.set_password(cfg["ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()
        app.logger.info("Bootstrap admin account created.")


if __name__ == "__main__":
    app = create_app()
    app.run(
        host=app.config["APP_HOST"],
        port=app.config["APP_PORT"],
        debug=app.config["DEBUG"],
    )
