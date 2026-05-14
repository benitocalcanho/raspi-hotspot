"""
Admin routes for user management, audit log, ngrok status, and system overview.
All endpoints require authentication. Some endpoints are admin-only.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import db
from models.user import User
from models.audit_log import AuditLog
from services.audit_service import log_event
from services import ngrok_service
from utils.decorators import require_roles
from utils.timezone_utils import get_effective_timezone_info, local_now



# Blueprint for all /api/admin endpoints
admin_bp = Blueprint("admin", __name__)
# Allowed roles for admin endpoints
ALLOWED_ROLES = ("admin", "user", "cleaner", "guest")

######################################################################
# Button press logging (frontend virtual button)
# This endpoint is called by the frontend when a user presses a door button.
# It logs the event and sends an email notification (async, non-blocking).
######################################################################
@admin_bp.route("/audit/button_press", methods=["POST"])
@jwt_required()
def log_button_press():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    button = data.get("button")

    # Log the button press event to the audit log
    log_event("button_press", user_id=user_id, detail={"button": button})


    # Send email notification in a background thread (non-blocking)
    from services.email_service import send_notification_email
    user = User.query.get(user_id)
    device = request.headers.get("User-Agent", "Unknown")
    subject = f"[Invisible Key] {button} pressed by {user.username}"
    body = f"User: {user.username}\nRole: {user.role}\nButton: {button}\nDevice: {device}"
    import threading
    from flask import current_app
    app = current_app._get_current_object() if hasattr(current_app, '_get_current_object') else current_app
    def send_email_async(subject, body, app):
        """Send email notification in a background thread with app context."""
        try:
            with app.app_context():
                send_notification_email(subject, body)
        except Exception as e:
            print(f"[Email Debug] Failed to send notification: {e}")

    threading.Thread(target=send_email_async, args=(subject, body, app), daemon=True).start()

    return jsonify({"status": "ok"}), 200

#
# Settings schema for the admin dashboard GUI.
# Each key defines a configurable field, its label, section, and type.
SETTINGS_SCHEMA = {
        # Email/SMTP notification settings
        "SMTP_HOST": {
            "label": "SMTP Host",
            "section": "email",
            "secret": False,
            "multiline": False,
            # Hostname of your SMTP server (e.g. smtp.gmail.com)
        },
        "SMTP_PORT": {
            "label": "SMTP Port",
            "section": "email",
            "secret": False,
            "multiline": False,
            # Port for SMTP server (usually 587 for TLS)
        },
        "SMTP_USER": {
            "label": "SMTP Username",
            "section": "email",
            "secret": True,
            "multiline": False,
            # Username for SMTP authentication
        },
        "SMTP_PASS": {
            "label": "SMTP Password",
            "section": "email",
            "secret": True,
            "multiline": False,
            # Password for SMTP authentication
        },
        "EMAIL_SENDER": {
            "label": "Sender Email",
            "section": "email",
            "secret": False,
            "multiline": False,
            # Email address that appears in the "From" field
        },
        "EMAIL_RECIPIENT": {
            "label": "Recipient Email",
            "section": "email",
            "secret": False,
            "multiline": False,
            # Email address that will receive notifications
        },
    "ICAL_URL": {
        "label": "Private iCal URL",
        "section": "ical",
        "secret": True,
        "multiline": False,
    },
    "ICAL_GUEST_PASSWORD": {
        "label": "Guest Password",
        "section": "ical",
        "secret": True,
        "multiline": False,
    },
    "CHECKOUT_TIME": {
        "label": "Check-out time (HH:MM)",
        "section": "schedule",
        "secret": False,
        "multiline": False,
    },
    "CHECKIN_TIME": {
        "label": "Check-in time (HH:MM)",
        "section": "schedule",
        "secret": False,
        "multiline": False,
    },
    "APP_TIMEZONE": {
        "label": "App Timezone (IANA, optional)",
        "section": "schedule",
        "secret": False,
        "multiline": False,
    },
    "NGROK_AUTHTOKEN": {
        "label": "Auth Token",
        "section": "ngrok",
        "secret": True,
        "multiline": False,
    },
    "NGROK_STATIC_DOMAIN": {
        "label": "Static Domain",
        "section": "ngrok",
        "secret": False,
        "multiline": False,
    },
    # Only iCal and general calendar settings remain
    "CALENDAR_GUEST_PASSWORD_MODE": {
        "label": "Guest Password Mode",
        "section": "calendar_rules",
        "secret": False,
        "multiline": False,
    },
    "CALENDAR_GUEST_DEFAULT_PASSWORD": {
        "label": "Guest Default Password (used when mode is 'fixed')",
        "section": "calendar_rules",
        "secret": True,
        "multiline": False,
    },
    "CLEANER_USERNAME": {
        "label": "Cleaner Username",
        "section": "cleaner",
        "secret": False,
        "multiline": False,
    },
    "CLEANER_PASSWORD": {
        "label": "Cleaner Password",
        "section": "cleaner",
        "secret": True,
        "multiline": False,
    },
}


def _admin_required(fn):
    """Combine JWT + admin role check."""
    return jwt_required()(require_roles("admin")(fn))


# ── Users ─────────────────────────────────────────────────────────────────────

@admin_bp.route("/users", methods=["GET"])
@_admin_required
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users]), 200


@admin_bp.route("/users", methods=["POST"])
@_admin_required
def create_user():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", "user")

    if not username or not password:
        return jsonify({"error": "username and password are required."}), 400
    if role not in ALLOWED_ROLES:
        return jsonify({"error": "role must be one of: admin, user, cleaner, guest."}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists."}), 409

    admin_id = int(get_jwt_identity())
    try:
        new_user = User(
            username=username,
            email=User.build_internal_email(username),
            role=role,
            created_by="manual",
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    log_event("user_created", user_id=admin_id, detail={"new_user": username})
    return jsonify(new_user.to_dict()), 201


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@_admin_required
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200


@admin_bp.route("/users/<int:user_id>", methods=["PATCH"])
@_admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}
    admin_id = int(get_jwt_identity())

    if "username" in data:
        new_username = data["username"].strip().lower()
        if not new_username:
            return jsonify({"error": "username cannot be empty."}), 400
        existing = User.query.filter(db.func.lower(User.username) == new_username).first()
        if existing and existing.id != user.id:
            return jsonify({"error": "Username already exists."}), 409
        user.username = new_username
        user.email = User.build_internal_email(new_username)

    if "role" in data:
        if data["role"] not in ALLOWED_ROLES:
            return jsonify({"error": "role must be one of: admin, user, cleaner, guest."}), 400
        user.role = data["role"]
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
    if "password" in data:
        try:
            user.set_password(data["password"])
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    db.session.commit()
    log_event("user_updated", user_id=admin_id, detail={"target_user_id": user_id})
    return jsonify(user.to_dict()), 200


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@_admin_required
def delete_user(user_id):
    admin_id = int(get_jwt_identity())
    if user_id == admin_id:
        return jsonify({"error": "You cannot delete your own account."}), 400

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    log_event("user_deleted", user_id=admin_id, detail={"deleted_user_id": user_id})
    return jsonify({"message": "User deleted."}), 200


# ── Audit log ─────────────────────────────────────────────────────────────────

@admin_bp.route("/audit", methods=["GET"])
@_admin_required
def audit_log():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)
    user_filter = request.args.get("user_id", type=int)
    event_filter = request.args.get("event", type=str)

    query = AuditLog.query.order_by(AuditLog.timestamp.desc())
    if user_filter:
        query = query.filter_by(user_id=user_filter)
    if event_filter:
        query = query.filter_by(event=event_filter)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "items": [entry.to_dict() for entry in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    }), 200


# ── ngrok status ──────────────────────────────────────────────────────────────

@admin_bp.route("/ngrok", methods=["GET"])
@_admin_required
def ngrok_status():
    url = ngrok_service.get_public_url()
    return jsonify({"url": url, "active": url is not None}), 200


@admin_bp.route("/ngrok/restart", methods=["POST"])
@_admin_required
def ngrok_restart():
    admin_id = int(get_jwt_identity())
    ngrok_service.stop_tunnel()
    from flask import current_app
    url = ngrok_service.start_tunnel(port=current_app.config["APP_PORT"], force=True)
    log_event("ngrok_restarted", user_id=admin_id, detail={"new_url": url})
    return jsonify({"url": url}), 200


# ── System overview ───────────────────────────────────────────────────────────

@admin_bp.route("/overview", methods=["GET"])
@_admin_required
def overview():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_events = AuditLog.query.count()
    ngrok_url = ngrok_service.get_public_url()
    tz_info = get_effective_timezone_info()
    now_dt = local_now()
    tz_name = tz_info["name"]
    tz_offset = int((now_dt.utcoffset().total_seconds() if now_dt.utcoffset() else 0) / 3600)
    now = now_dt.isoformat()
    return jsonify({
        "total_users": total_users,
        "active_users": active_users,
        "total_audit_events": total_events,
        "ngrok_url": ngrok_url,
        "system_time": now,
        "timezone_name": tz_name,
        "timezone_offset": tz_offset,
        "timezone_source": tz_info["source"],
    }), 200


# ── Scheduler control ─────────────────────────────────────────────────────────

@admin_bp.route("/scheduler/restart", methods=["POST"])
@_admin_required
def restart_scheduler():
    """Restart the APScheduler with the current checkout/checkin times from config.
    Use this after changing schedule times in Settings so they take effect immediately.
    """
    from flask import current_app
    from services.calendar_service import start_scheduler

    admin_id = int(get_jwt_identity())

    # Stop existing scheduler if running
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        import apscheduler
        # Access the running scheduler via the module-level reference if available
        from services import calendar_service as _cs
        if hasattr(_cs, "_scheduler") and _cs._scheduler and _cs._scheduler.running:
            _cs._scheduler.shutdown(wait=False)
    except Exception:
        pass

    start_scheduler(current_app)
    tz_info = get_effective_timezone_info(app=current_app)
    log_event("scheduler_restarted", user_id=admin_id, detail={
        "checkout": current_app.config.get("CHECKOUT_TIME"),
        "checkin": current_app.config.get("CHECKIN_TIME"),
        "timezone": tz_info["name"],
    })
    return jsonify({
        "message": "Scheduler restarted.",
        "checkout_time": current_app.config.get("CHECKOUT_TIME", "12:00"),
        "checkin_time": current_app.config.get("CHECKIN_TIME", "14:00"),
        "timezone": tz_info["name"],
        "timezone_source": tz_info["source"],
    }), 200


# ── App settings ──────────────────────────────────────────────────────────────

@admin_bp.route("/settings", methods=["GET"])
@_admin_required
def get_settings():
    """Return the settings schema and current values. Secrets are masked."""
    from flask import current_app
    from models.setting import Setting

    values = {}
    for key, meta in SETTINGS_SCHEMA.items():
        db_val = Setting.get(key)
        if db_val is not None:
            raw = db_val
        else:
            # Fall back to app.config (populated from env vars) so defaults are
            # visible on first install before anything has been saved via the dashboard.
            raw = current_app.config.get(key, "") or ""
        values[key] = {
            "is_set": bool(raw),
            "value": raw,
        }

    return jsonify({"schema": SETTINGS_SCHEMA, "values": values}), 200



@admin_bp.route("/settings", methods=["PATCH"])
@_admin_required
def update_settings():
    """Persist one or more settings. Empty strings are ignored (keeps existing value).
    Special handling for cleaner account: update or create the single cleaner user.
    """
    from flask import current_app
    from models.setting import Setting

    data = request.get_json(silent=True) or {}
    admin_id = int(get_jwt_identity())

    updated = []

    cleaner_username = data.get("CLEANER_USERNAME", "").strip()
    cleaner_password = data.get("CLEANER_PASSWORD", "").strip()
    # If either cleaner field is present, require both
    if ("CLEANER_USERNAME" in data or "CLEANER_PASSWORD" in data):
        if not cleaner_username or not cleaner_password:
            return jsonify({"error": "Both cleaner username and password are required."}), 400
        from models.user import User
        # Remove all other cleaner accounts
        for other in User.query.filter(User.role == "cleaner", User.username != cleaner_username):
            db.session.delete(other)
        # Check for username conflict
        existing = User.query.filter_by(username=cleaner_username).first()
        if existing and existing.role != "cleaner":
            return jsonify({"error": "Username already exists for a non-cleaner account."}), 409
        cleaner = User.query.filter_by(role="cleaner").first()
        if not cleaner:
            cleaner = User(
                username=cleaner_username,
                email=User.build_internal_email(cleaner_username),
                role="cleaner",
                created_by="manual",
            )
            db.session.add(cleaner)
        else:
            cleaner.username = cleaner_username
            cleaner.email = User.build_internal_email(cleaner_username)
        try:
            cleaner.set_password(cleaner_password)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        Setting.set("CLEANER_USERNAME", cleaner_username)
        Setting.set("CLEANER_PASSWORD", cleaner_password)
        updated.append("CLEANER_USERNAME")
        updated.append("CLEANER_PASSWORD")
        db.session.commit()

    # Handle all other settings
    for key, value in data.items():
        if key not in SETTINGS_SCHEMA or key.startswith("CLEANER_"):
            continue
        value = str(value).strip() if value is not None else ""
        if not value:
            continue  # empty field = keep existing, don't overwrite with blank
        Setting.set(key, value)
        current_app.config[key] = value  # take effect immediately without restart
        updated.append(key)
    db.session.commit()

    # Restart ngrok tunnel if its config changed. Do the slow tunnel open in
    # the background so the settings save button returns quickly on small Pis.
    ngrok_restarting = False
    if "NGROK_AUTHTOKEN" in updated or "NGROK_STATIC_DOMAIN" in updated:
        app = current_app._get_current_object()
        port = current_app.config.get("APP_PORT", 5000)
        ngrok_service.stop_tunnel()

        def restart_ngrok_async() -> None:
            try:
                with app.app_context():
                    ngrok_service.start_tunnel(port=port, force=True)
            except Exception as exc:
                app.logger.warning("ngrok async restart failed: %s", exc)

        import threading
        threading.Thread(target=restart_ngrok_async, daemon=True).start()
        ngrok_restarting = True

    log_event("settings_updated", user_id=admin_id, detail={"keys": updated})
    return jsonify({"updated": updated, "ngrok_restarting": ngrok_restarting}), 200
