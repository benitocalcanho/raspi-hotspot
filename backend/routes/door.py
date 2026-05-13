from flask import Blueprint, jsonify, request
from services.reed_sensor_service import reed_sensor
from models.door_log import DoorLog
from models import db

bp = Blueprint('door', __name__, url_prefix='/api/door')

@bp.route('/status', methods=['GET'])
def status():
    state = reed_sensor.get_state()
    log = DoorLog.query.order_by(DoorLog.timestamp.desc()).first()
    return jsonify({
        'state': state,
        'timestamp': log.timestamp.isoformat() if log else None
    })

@bp.route('/log', methods=['GET'])
def log():
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    logs = DoorLog.query.order_by(DoorLog.timestamp.desc()).offset(offset).limit(limit).all()
    return jsonify([
        {'timestamp': l.timestamp.isoformat(), 'state': l.state} for l in logs
    ])
