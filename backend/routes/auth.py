"""
Authentication routes — login, logout, refresh, password change.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from flask import current_app

from models.user import User
from models import db
from services.audit_service import log_event
from utils.guest_access import guest_stay_has_ended
from utils.decorators import current_user_or_response


auth_bp = Blueprint("auth", __name__)

_LOGIN_ATTEMPT_WINDOW_SECONDS = 10 * 60
_MAX_FAILED_LOGIN_ATTEMPTS = 5
_failed_login_attempts = {}


def _request_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    forwarded_ip = forwarded_for.split(",")[0].strip() if forwarded_for else ""
    return forwarded_ip or request.headers.get("X-Real-IP", "") or request.remote_addr or "unknown"


def _login_attempt_key(username: str):
    return (_request_ip(), username)


def _recent_failures(key):
    from time import monotonic
    now = monotonic()
    attempts = [ts for ts in _failed_login_attempts.get(key, []) if now - ts < _LOGIN_ATTEMPT_WINDOW_SECONDS]
    if attempts:
        _failed_login_attempts[key] = attempts
    else:
        _failed_login_attempts.pop(key, None)
    return attempts


def _is_rate_limited(key) -> bool:
    return len(_recent_failures(key)) >= _MAX_FAILED_LOGIN_ATTEMPTS


def _record_failed_login(key) -> None:
    from time import monotonic
    attempts = _recent_failures(key)
    attempts.append(monotonic())
    _failed_login_attempts[key] = attempts


def _clear_failed_logins(key) -> None:
    _failed_login_attempts.pop(key, None)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    attempt_key = _login_attempt_key(username)
    if _is_rate_limited(attempt_key):
        log_event("login_rate_limited", detail={"username": username})
        return jsonify({"error": "Too many failed login attempts. Try again later."}), 429

    # Case-insensitive username lookup
    user = User.query.filter(db.func.lower(User.username) == username).first()

    if not user or not user.is_active or not user.check_password(password):
        _record_failed_login(attempt_key)
        # Log failed attempt (user_id may be None if username not found)
        log_event(
            "login_failed",
            user_id=user.id if user else None,
            detail={"username": username},
        )
        return jsonify({"error": "Invalid credentials."}), 401

    if guest_stay_has_ended(user.valid_until, app=current_app):
        log_event("login_failed", user_id=user.id, detail={"username": username, "reason": "stay_ended"})
        return jsonify({"error": "Your stay has ended."}), 403

    additional_claims = {"role": user.role, "username": user.username}
    access_token = create_access_token(identity=str(user.id), additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=additional_claims)

    _clear_failed_logins(attempt_key)
    log_event("login_success", user_id=user.id)

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict(),
    }), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid session."}), 401

    user = User.query.get(user_id)
    if not user or not user.is_active:
        return jsonify({"error": "Account inactive or not found."}), 401
    if user.role == "guest" and guest_stay_has_ended(user.valid_until, app=current_app):
        return jsonify({"error": "Your stay has ended."}), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "username": user.username},
    )
    return jsonify({"access_token": access_token}), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    user, error = current_user_or_response()
    if error:
        return error
    log_event("logout", user_id=user.id)
    # JWT is stateless; client discards tokens. For token revocation, add a
    # blocklist (Redis or DB table) here when needed.
    return jsonify({"message": "Logged out."}), 200


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    user, error = current_user_or_response()
    if error:
        return error
    user_id = user.id
    data = request.get_json(silent=True) or {}
    current_pw = data.get("current_password", "")
    new_pw = data.get("new_password", "")

    if not current_pw or not new_pw:
        return jsonify({"error": "current_password and new_password are required."}), 400

    if not user.check_password(current_pw):
        log_event("password_change_failed", user_id=user_id)
        return jsonify({"error": "Current password is incorrect."}), 403

    try:
        user.set_password(new_pw)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    from models import db
    db.session.commit()
    log_event("password_changed", user_id=user_id)
    return jsonify({"message": "Password updated."}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user, error = current_user_or_response()
    if error:
        return error
    return jsonify(user.to_dict()), 200
