"""GPIO routes."""
import threading
import time

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from flask import current_app

from services import gpio_service
from services.audit_service import log_event
from utils.decorators import require_roles
from utils.guest_access import guest_stay_has_ended

gpio_bp = Blueprint("gpio", __name__)
MAX_PULSE_SECONDS = 30


@gpio_bp.route("/pins", methods=["GET"])
@jwt_required()
@require_roles("admin")
def list_pins():
    pins = gpio_service.get_all_pins()
    # Sync live hardware state into DB before returning so the UI is accurate
    result = []
    for p in pins:
        try:
            gpio_service.read_pin_state(p.pin_number)  # syncs live→DB
        except Exception:
            pass
        result.append(p.to_dict())
    return jsonify(result), 200


@gpio_bp.route("/pins", methods=["POST"])
@jwt_required()
@require_roles("admin")
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
@require_roles("admin")
def get_pin(pin_number):
    try:
        state = gpio_service.read_pin_state(pin_number)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"pin_number": pin_number, "state": state}), 200


@gpio_bp.route("/pins/<int:pin_number>/toggle", methods=["POST"])
@jwt_required()
@require_roles("admin")
def toggle_pin(pin_number):
    from flask import request
    from models.user import User
    from services.email_service import send_notification_email
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

    # Gather details for email
    user = User.query.get(user_id)
    if user and guest_stay_has_ended(user.valid_until, app=current_app):
        return jsonify({"error": "Your stay has ended."}), 403
    device = request.headers.get("User-Agent", "Unknown")
    button_label = getattr(pin, "label", f"Pin {pin_number}")
    action = "Unlocked" if pin.state else "Locked"
    subject = f"[Invisible Key] {action} by {user.username}"
    body = f"User: {user.username}\nRole: {user.role}\nButton: {button_label}\nPin: {pin_number}\nAction: {action}\nDevice: {device}"
    try:
        send_notification_email(subject, body)
    except Exception as e:
        # Log but do not block the action
        print(f"[Email] Failed to send notification: {e}")

    log_event("gpio_toggle", user_id=user_id, detail={"pin": pin_number, "new_state": pin.state})
    return jsonify(pin.to_dict()), 200


@gpio_bp.route("/pins/<int:pin_number>/set", methods=["POST"])
@jwt_required()
@require_roles("admin")
def set_pin(pin_number):
    """Explicitly set a pin to ON or OFF. Used for reliable pulse control."""
    data = request.get_json(silent=True) or {}
    state = data.get("state")
    if state is None:
        return jsonify({"error": "state (true/false) is required."}), 400
    try:
        pin = gpio_service.set_pin_state(pin_number, bool(state))
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(pin.to_dict()), 200


@gpio_bp.route("/pins/<int:pin_number>/pulse", methods=["POST"])
@jwt_required()
def pulse_pin(pin_number):
    """Turn an output on briefly, then force it off server-side."""
    from models.user import User

    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user or not user.is_active:
        return jsonify({"error": "User is inactive."}), 403
    if user.role not in ("admin", "user", "cleaner", "guest"):
        return jsonify({"error": "Insufficient permissions."}), 403
    if user.role == "guest" and guest_stay_has_ended(user.valid_until, app=current_app):
        return jsonify({"error": "Your stay has ended."}), 403

    data = request.get_json(silent=True) or {}
    requested = data.get("duration", 5)
    try:
        duration = min(max(float(requested), 0.1), MAX_PULSE_SECONDS)
        pin = gpio_service.set_pin_state(pin_number, True)
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404

    app = current_app._get_current_object()

    def turn_off_later() -> None:
        time.sleep(duration)
        with app.app_context():
            try:
                gpio_service.set_pin_state(pin_number, False)
                log_event("gpio_pulse_ended", detail={"pin": pin_number, "duration": duration})
            except Exception as exc:
                app.logger.warning("Failed to end GPIO%s pulse: %s", pin_number, exc)

    threading.Thread(target=turn_off_later, daemon=True).start()
    log_event("gpio_pulse_started", user_id=user_id, detail={"pin": pin_number, "duration": duration})
    return jsonify({**pin.to_dict(), "pulse_duration": duration}), 200



@gpio_bp.route("/pins/<int:pin_number>", methods=["DELETE"])
@jwt_required()
@require_roles("admin")
def delete_pin(pin_number):
    try:
        gpio_service.delete_pin(pin_number)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404

    admin_id = int(get_jwt_identity())
    log_event("gpio_pin_deleted", user_id=admin_id, detail={"pin": pin_number})
    return jsonify({"message": f"Pin BCM{pin_number} removed."}), 200
