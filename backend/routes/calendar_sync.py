"""
Calendar sync routes — admin can manually trigger a sync or view sync status.
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.calendar_service import sync_calendar
from services.audit_service import log_event
from utils.decorators import require_roles

calendar_bp = Blueprint("calendar", __name__)


@calendar_bp.route("/sync", methods=["POST"])
@jwt_required()
@require_roles("admin")
def trigger_sync():
    """Manually trigger a Google Calendar sync."""
    from flask import current_app as app
    admin_id = int(get_jwt_identity())
    created = sync_calendar(app._get_current_object())
    log_event("calendar_sync_triggered", user_id=admin_id, detail={"users_created": created})
    return jsonify({"users_created": created}), 200
