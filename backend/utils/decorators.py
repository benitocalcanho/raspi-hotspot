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


def tailscale_required(fn):
    """
    Decorator: reject requests that do NOT originate from the
    Tailscale subnet (100.64.0.0/10 by default).

    Should be combined with @require_roles('admin') on admin endpoints
    so that even if someone guesses a valid JWT, they must be on Tailscale.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        tailscale_subnet = ip_network(
            current_app.config.get("TAILSCALE_SUBNET", "100.64.0.0/10")
        )
        # Respect X-Forwarded-For set by a trusted reverse proxy
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        client_ip_str = forwarded_for.split(",")[0].strip() if forwarded_for else request.remote_addr

        try:
            client_ip = ip_address(client_ip_str)
        except ValueError:
            return jsonify({"error": "Invalid client IP."}), 400

        if client_ip not in tailscale_subnet:
            return jsonify({"error": "Admin access requires Tailscale."}), 403

        return fn(*args, **kwargs)
    return wrapper
