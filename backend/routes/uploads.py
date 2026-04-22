"""
Image upload routes — admin can upload door photos served to the guest dashboard.
Images are stored in backend/uploads/ and served at /api/uploads/<filename>.
"""
import os
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from flask_jwt_extended import jwt_required
from utils.decorators import require_roles

uploads_bp = Blueprint("uploads", __name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
DOOR_KEYS = ("building_door", "apartment_door")


def _uploads_dir():
    return os.path.join(os.path.dirname(__file__), "..", "uploads")


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _current_images():
    """Return dict of door_key → URL path (or None if not uploaded yet)."""
    result = {}
    udir = _uploads_dir()
    for key in DOOR_KEYS:
        found = None
        for ext in ALLOWED_EXTENSIONS:
            candidate = os.path.join(udir, f"{key}.{ext}")
            if os.path.exists(candidate):
                found = f"/api/uploads/{key}.{ext}"
                break
        result[key] = found
    return result


@uploads_bp.route("/<filename>")
def serve_image(filename):
    """Serve an uploaded image. No auth required — guests need to load these."""
    return send_from_directory(_uploads_dir(), filename)


@uploads_bp.route("/images", methods=["GET"])
def get_images():
    """Return current image URLs for both doors."""
    return jsonify(_current_images()), 200


@uploads_bp.route("/images/<door_key>", methods=["POST"])
@jwt_required()
@require_roles("admin")
def upload_image(door_key):
    """Upload a door image. door_key must be 'building_door' or 'apartment_door'."""
    if door_key not in DOOR_KEYS:
        return jsonify({"error": "Invalid door key. Use 'building_door' or 'apartment_door'."}), 400

    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    file = request.files["file"]
    if not file.filename or not _allowed(file.filename):
        return jsonify({"error": "Invalid file type. Use jpg, png, or webp."}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    udir = _uploads_dir()
    os.makedirs(udir, exist_ok=True)

    # Remove any previous file for this key (different extension)
    for old_ext in ALLOWED_EXTENSIONS:
        old_path = os.path.join(udir, f"{door_key}.{old_ext}")
        if os.path.exists(old_path):
            os.remove(old_path)

    save_path = os.path.join(udir, f"{door_key}.{ext}")
    file.save(save_path)

    return jsonify({"url": f"/api/uploads/{door_key}.{ext}"}), 200
