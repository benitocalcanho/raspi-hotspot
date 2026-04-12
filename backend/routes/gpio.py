"""
GPIO routes — admin can configure pins; any authenticated user can read/toggle
pins that are assigned to them (future: per-pin ACL).
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from services import gpio_service
from services.audit_service import log_event
from utils.decorators import require_roles, tailscale_required

gpio_bp = Blueprint("gpio", __name__)


@gpio_bp.route("/pins", methods=["GET"])
@jwt_required()
def list_pins():
    pins = gpio_service.get_all_pins()
    return jsonify([p.to_dict() for p in pins]), 200


@gpio_bp.route("/pins", methods=["POST"])
@jwt_required()
@require_roles("admin")
@tailscale_required
def add_pin():
    data = request.get_json(silent=True) or {}
    pin_number = data.get("pin_number")
    label = data.get("label", "")
    direction = data.get("direction", "output")

    if pin_number is None:
        return jsonify({"error": "pin_number is required."}), 400

    try:
        pin = gpio_service.configure_pin(int(pin_number), label, direction)
    except (ValueError, Exception) as exc:
        return jsonify({"error": str(exc)}), 400

    admin_id = int(get_jwt_identity())
    log_event("gpio_pin_added", user_id=admin_id, detail={"pin": pin_number, "label": label})
    return jsonify(pin.to_dict()), 201


@gpio_bp.route("/pins/<int:pin_number>", methods=["GET"])
@jwt_required()
def get_pin(pin_number):
    try:
        state = gpio_service.read_pin_state(pin_number)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"pin_number": pin_number, "state": state}), 200


@gpio_bp.route("/pins/<int:pin_number>/toggle", methods=["POST"])
@jwt_required()
def toggle_pin(pin_number):
    claims = get_jwt()
    role = claims.get("role")
    user_id = int(get_jwt_identity())

    try:
        current_state = gpio_service.read_pin_state(pin_number)
        pin = gpio_service.set_pin_state(pin_number, not current_state)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    log_event("gpio_toggle", user_id=user_id, detail={"pin": pin_number, "new_state": pin.state})
    return jsonify(pin.to_dict()), 200


@gpio_bp.route("/pins/<int:pin_number>", methods=["DELETE"])
@jwt_required()
@require_roles("admin")
@tailscale_required
def delete_pin(pin_number):
    try:
        gpio_service.delete_pin(pin_number)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404

    admin_id = int(get_jwt_identity())
    log_event("gpio_pin_deleted", user_id=admin_id, detail={"pin": pin_number})
    return jsonify({"message": f"Pin BCM{pin_number} removed."}), 200
