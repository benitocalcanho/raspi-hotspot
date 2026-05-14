from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from models.door_log import DoorLog
from services.reed_sensor_service import reed_sensor
from utils.decorators import require_roles

door_bp = Blueprint("door", __name__)


@door_bp.route("/status", methods=["GET"])
@jwt_required()
@require_roles("admin")
def status():
    latest = DoorLog.query.order_by(DoorLog.timestamp.desc()).first()
    payload = reed_sensor.status()
    payload["last_event"] = latest.to_dict() if latest else None
    return jsonify(payload), 200


@door_bp.route("/events", methods=["GET"])
@jwt_required()
@require_roles("admin")
def events():
    limit = min(int(request.args.get("limit", 50)), 200)
    rows = DoorLog.query.order_by(DoorLog.timestamp.desc()).limit(limit).all()
    return jsonify([row.to_dict() for row in rows]), 200
