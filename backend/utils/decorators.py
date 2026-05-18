"""
Route decorators for role-based access control.
"""
from functools import wraps

from flask import current_app, g, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from utils.guest_access import guest_stay_has_ended


def current_user_or_response():
    """Return the current active DB user, or a Flask error response tuple."""
    verify_jwt_in_request()
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None, (jsonify({"error": "Invalid session."}), 401)

    from models.user import User

    user = User.query.get(user_id)
    if not user or not user.is_active:
        return None, (jsonify({"error": "Account inactive or not found."}), 401)
    if user.role == "guest" and guest_stay_has_ended(user.valid_until, app=current_app):
        return None, (jsonify({"error": "Your stay has ended."}), 401)

    g.current_user = user
    return user, None


def require_active_user(fn):
    """Decorator: allow only active users that still exist in the database."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        _user, error = current_user_or_response()
        if error:
            return error
        return fn(*args, **kwargs)
    return wrapper


def require_roles(*roles):
    """Decorator: allow only active DB users whose current role is in roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user, error = current_user_or_response()
            if error:
                return error
            if user.role not in roles:
                return jsonify({"error": "Insufficient permissions."}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
