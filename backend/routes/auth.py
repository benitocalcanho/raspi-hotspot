"""
Authentication routes — login, logout, refresh, password change.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)
from datetime import date

from models.user import User
from models import db
from services.audit_service import log_event

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    # Case-insensitive username lookup
    user = User.query.filter(db.func.lower(User.username) == username).first()

    if not user or not user.is_active or not user.check_password(password):
        # Log failed attempt (user_id may be None if username not found)
        log_event(
            "login_failed",
            user_id=user.id if user else None,
            detail={"username": username},
        )
        return jsonify({"error": "Invalid credentials."}), 401

    if user.valid_until and date.today() >= user.valid_until:
        log_event("login_failed", user_id=user.id, detail={"username": username, "reason": "stay_ended"})
        return jsonify({"error": "Your stay has ended."}), 403

    additional_claims = {"role": user.role, "username": user.username}
    access_token = create_access_token(identity=str(user.id), additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=additional_claims)

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
    claims = get_jwt()
    user = User.query.get(int(identity))
    if user and user.valid_until and date.today() >= user.valid_until:
        return jsonify({"error": "Your stay has ended."}), 401
    access_token = create_access_token(
        identity=identity,
        additional_claims={"role": claims.get("role"), "username": claims.get("username")},
    )
    return jsonify({"access_token": access_token}), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    user_id = int(get_jwt_identity())
    log_event("logout", user_id=user_id)
    # JWT is stateless; client discards tokens. For token revocation, add a
    # blocklist (Redis or DB table) here when needed.
    return jsonify({"message": "Logged out."}), 200


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    current_pw = data.get("current_password", "")
    new_pw = data.get("new_password", "")

    if not current_pw or not new_pw:
        return jsonify({"error": "current_password and new_password are required."}), 400

    user = User.query.get(user_id)
    if not user or not user.check_password(current_pw):
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
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404
    return jsonify(user.to_dict()), 200
