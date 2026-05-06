"""
WiFi setup routes — used during first-boot hotspot onboarding.
Endpoints:
    /api/wifi/status: Get current WiFi connection status
    /api/wifi/scan: Scan for available WiFi networks
    /api/wifi/connect: Connect to a WiFi network
    /api/wifi/teardown: Admin can tear down the hotspot
After initial setup is complete these endpoints are not normally reachable
(hotspot is torn down and the Pi is on the local network).
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from services import wifi_service
from services.audit_service import log_event
from utils.decorators import require_roles

wifi_bp = Blueprint("wifi", __name__)


@wifi_bp.route("/status", methods=["GET"])
@jwt_required()
def status():
    return jsonify(wifi_service.get_connection_status()), 200


@wifi_bp.route("/scan", methods=["GET"])
def scan():
    """Scan for available WiFi networks. No auth required during hotspot setup."""
    try:
        networks = wifi_service.scan_networks()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify(networks), 200


@wifi_bp.route("/connect", methods=["POST"])
def connect():
    """
    Connect to a WiFi network. No auth required during hotspot setup phase.
    After connecting, the admin should change credentials via the admin dashboard.
    """
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
