"""
User routes — each authenticated user sees only their own data.
Endpoints:
    /api/user/dashboard: Returns dashboard data for the authenticated user
    /api/user/activity: Returns audit log for the authenticated user
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from utils.decorators import current_user_or_response
from models.audit_log import AuditLog

user_bp = Blueprint("user", __name__)


@user_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    """Return dashboard data for the currently authenticated user."""
    user, error = current_user_or_response()
    if error:
        return error
    user_id = user.id

    # Last 10 login events for this user
    recent_logins = (
        AuditLog.query
        .filter_by(user_id=user_id)
        .filter(AuditLog.event.in_(["login_success", "login_failed"]))
        .order_by(AuditLog.timestamp.desc())
        .limit(10)
        .all()
    )

    return jsonify({
        "user": user.to_dict(),
        "recent_logins": [e.to_dict() for e in recent_logins],
    }), 200


@user_bp.route("/activity", methods=["GET"])
@jwt_required()
def activity():
    """Return the full audit trail for the currently authenticated user."""
    user, error = current_user_or_response()
    if error:
        return error
    user_id = user.id
    logs = (
        AuditLog.query
        .filter_by(user_id=user_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(100)
        .all()
    )
    return jsonify([e.to_dict() for e in logs]), 200
