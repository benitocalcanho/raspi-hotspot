"""
Route decorators for role-based and network-based access control.
"""
from functools import wraps
from ipaddress import ip_address, ip_network
from flask import request, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def require_roles(*roles):
    """Decorator: allow only users whose JWT role is in `roles`."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("role") not in roles:
                return jsonify({"error": "Insufficient permissions."}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

