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
    reed_sensor.poll_once(source="sensor_status")
    latest = DoorLog.query.order_by(DoorLog.timestamp.desc()).first()
    payload = reed_sensor.status()
    payload["last_event"] = latest.to_dict() if latest else None
    return jsonify(payload), 200


@door_bp.route("/events", methods=["GET"])
@jwt_required()
@require_roles("admin")
def events():
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    limit = min(max(request.args.get("limit", 50, type=int) or 50, 1), 200)
    pagination = (
        DoorLog.query
        .order_by(DoorLog.timestamp.desc())
        .paginate(page=page, per_page=limit, error_out=False)
    )
    return jsonify({
        "items": [row.to_dict() for row in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    }), 200
