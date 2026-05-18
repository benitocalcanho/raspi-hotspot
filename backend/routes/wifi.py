"""WiFi routes for admin-managed network setup."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from services import wifi_service
from services.audit_service import log_event
from utils.decorators import require_roles

wifi_bp = Blueprint("wifi", __name__)


@wifi_bp.route("/status", methods=["GET"])
@jwt_required()
@require_roles("admin")
def status():
    return jsonify(wifi_service.get_connection_status()), 200


@wifi_bp.route("/scan", methods=["GET"])
@jwt_required()
@require_roles("admin")
def scan():
    """Scan for available WiFi networks."""
    try:
        networks = wifi_service.scan_networks()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify(networks), 200


@wifi_bp.route("/connect", methods=["POST"])
@jwt_required()
@require_roles("admin")
def connect():
    """Connect to a WiFi network."""
    data = request.get_json(silent=True) or {}
    ssid = data.get("ssid", "").strip()
    passphrase = data.get("passphrase", "")

    if not ssid or not passphrase:
        return jsonify({"error": "ssid and passphrase are required."}), 400

    try:
        result = wifi_service.connect_to_network(ssid, passphrase)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(result), 200


@wifi_bp.route("/hotspot/stop", methods=["POST"])
@jwt_required()
@require_roles("admin")
def stop_hotspot():
    """Admin can tear down the hotspot once the Pi is connected."""
    result = wifi_service.stop_hotspot()
    log_event("hotspot_stopped", user_id=None)
    return jsonify(result), 200


# ── Admin WiFi management ─────────────────────────────────────────────────────

@wifi_bp.route("/admin/status", methods=["GET"])
@jwt_required()
@require_roles("admin")
def admin_status():
    """Return current WiFi connection status."""
    return jsonify(wifi_service.get_connection_status()), 200


@wifi_bp.route("/admin/scan", methods=["GET"])
@jwt_required()
@require_roles("admin")
def admin_scan():
    """Scan for nearby WiFi networks (admin only)."""
    try:
        networks = wifi_service.scan_networks()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify(networks), 200


@wifi_bp.route("/admin/saved", methods=["GET"])
@jwt_required()
@require_roles("admin")
def list_saved():
    """List WiFi networks saved in NetworkManager."""
    return jsonify(wifi_service.list_saved_networks()), 200


@wifi_bp.route("/admin/saved", methods=["POST"])
@jwt_required()
@require_roles("admin")
def add_saved():
    """Store WiFi credentials without connecting. Pi will auto-connect when in range."""
    from flask_jwt_extended import get_jwt_identity
    data = request.get_json(silent=True) or {}
    ssid = data.get("ssid", "").strip()
    passphrase = data.get("passphrase", "")
    if not ssid or not passphrase:
        return jsonify({"error": "ssid and passphrase are required."}), 400
    try:
        result = wifi_service.save_network_profile(ssid, passphrase)
    except (ValueError, Exception) as exc:
        return jsonify({"error": str(exc)}), 400
    admin_id = int(get_jwt_identity())
    log_event("wifi_network_saved", user_id=admin_id, detail={"ssid": ssid})
    return jsonify(result), 200


@wifi_bp.route("/admin/saved/<name>", methods=["DELETE"])
@jwt_required()
@require_roles("admin")
def delete_saved(name):
    """Delete a saved WiFi connection profile."""
    from flask_jwt_extended import get_jwt_identity
    try:
        result = wifi_service.delete_saved_network(name)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    admin_id = int(get_jwt_identity())
    log_event("wifi_network_deleted", user_id=admin_id, detail={"name": name})
    return jsonify(result), 200


@wifi_bp.route("/admin/saved/<name>/connect", methods=["POST"])
@jwt_required()
@require_roles("admin")
def connect_saved(name):
    """Activate a saved WiFi connection profile."""
    from flask_jwt_extended import get_jwt_identity
    try:
        result = wifi_service.connect_saved_network(name)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    admin_id = int(get_jwt_identity())
    log_event("wifi_connect_saved", user_id=admin_id, detail={"name": name})
    return jsonify(result), 200
