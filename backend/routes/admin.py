"""
Admin routes — accessible only via Tailscale (enforced by @tailscale_required).
Covers user CRUD, audit log viewing, ngrok status, and system overview.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import db
from models.user import User
from models.audit_log import AuditLog
from services.audit_service import log_event
from services import ngrok_service
from utils.decorators import require_roles, tailscale_required

admin_bp = Blueprint("admin", __name__)


def _admin_required(fn):
    """Combine JWT + admin role + Tailscale network check."""
    return jwt_required()(require_roles("admin")(tailscale_required(fn)))


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
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    role = data.get("role", "user")

    if not username or not email or not password:
        return jsonify({"error": "username, email, and password are required."}), 400
    if role not in ("admin", "user"):
        return jsonify({"error": "role must be 'admin' or 'user'."}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists."}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists."}), 409

    admin_id = int(get_jwt_identity())
    try:
        new_user = User(username=username, email=email, role=role, created_by="manual")
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

    if "email" in data:
        user.email = data["email"].strip()
    if "role" in data:
        if data["role"] not in ("admin", "user"):
            return jsonify({"error": "role must be 'admin' or 'user'."}), 400
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

    query = AuditLog.query.order_by(AuditLog.timestamp.desc())
    if user_filter:
        query = query.filter_by(user_id=user_filter)

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
    url = ngrok_service.start_tunnel(port=current_app.config["APP_PORT"])
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
    return jsonify({
        "total_users": total_users,
        "active_users": active_users,
        "total_audit_events": total_events,
        "ngrok_url": ngrok_url,
    }), 200
