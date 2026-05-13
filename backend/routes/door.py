from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from services.reed_sensor_service import reed_sensor
from models.door_log import DoorLog
from utils.decorators import require_roles

bp = Blueprint("door", __name__, url_prefix="/api/door")


@bp.route("/status", methods=["GET"])
@jwt_required()
@require_roles("admin")
def status():
    log = DoorLog.query.order_by(DoorLog.timestamp.desc()).first()
    payload = reed_sensor.status()
    payload["timestamp"] = log.timestamp.isoformat() if log else None
    return jsonify(payload), 200


@bp.route("/log", methods=["GET"])
@jwt_required()
@require_roles("admin")
def log():
    limit = max(1, min(request.args.get("limit", 50, type=int), 200))
    offset = max(request.args.get("offset", 0, type=int), 0)
    logs = DoorLog.query.order_by(DoorLog.timestamp.desc()).offset(offset).limit(limit).all()
    return jsonify([
        {"timestamp": l.timestamp.isoformat(), "state": l.state, "source": l.source} for l in logs
    ]), 200
