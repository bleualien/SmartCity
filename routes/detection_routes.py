# server/routes/detection_routes.py

from flask import Blueprint, request, jsonify
import logging
import os

from services.inference_service import InferenceService
from model_loader import ModelLoader
from utils.file_utils import save_upload

from controller.detection_controller import (
    create_detection,
    get_my_single,
    get_my_detections,
    get_my_by_type,
    update_my_detection,
    delete_my_detection,
    delete_all_my_by_type
)

logger = logging.getLogger(__name__)

# -------------------------------------------------
# ML DETECTION ROUTE (Unified)
# -------------------------------------------------
detect_ml_bp = Blueprint("detect_ml", __name__)

model_loader = ModelLoader(
    waste_model_path="runs/detect/waste_yolo_fast/weights/waste.pt",
    pothole_model_path="runs/pothole_yolov8/weights/best.pt"
)
inference = InferenceService(model_loader)


@detect_ml_bp.route("/detects", methods=["POST"])
def detect_route():
    try:
        # Extract from either form-data or JSON
        json_data = request.get_json(silent=True) or {}

        # Form-data
        user_id = request.form.get("user_id") if request.form else json_data.get("user_id")
        task_type = request.form.get("task_type") if request.form else json_data.get("task_type", "waste")
        task_type = task_type or "waste"

        # -------------------------------------------------
        # CASE 1 — PRIMARY DETECTION: file upload
        # -------------------------------------------------
        if "image" in request.files:
            file = request.files["image"]
            saved_path = save_upload(file)  # you already use this

            result = inference.run(
                image_path=saved_path,
                user_id=user_id,
                task_type=task_type
            )
            return jsonify(result), 200

        # -------------------------------------------------
        # CASE 2 — SECONDARY DETECTION: reuse stored image
        # -------------------------------------------------
        image_name = json_data.get("image_name")

        if image_name:
            # Select correct folder based on type
            if task_type == "waste":
                folder = "storage/waste/detected"
            elif task_type == "pothole":
                folder = "storage/pothole"
            else:
                return jsonify({"success": False, "error": "Invalid task_type"}), 400

            img_path = os.path.join(folder, image_name)

            if not os.path.exists(img_path):
                return jsonify({
                    "success": False,
                    "error": "Image not found",
                    "path": img_path
                }), 404

            result = inference.run(
                image_path=img_path,
                user_id=user_id,
                task_type=task_type
            )

            return jsonify(result), 200

        # -------------------------------------------------
        # CASE 3 — Nothing sent
        # -------------------------------------------------
        return jsonify({
            "success": False,
            "error": "No file or image_name provided"
        }), 400

    except Exception as e:
        logger.exception("Detection API error")
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------------------------------------
# DATABASE ROUTES
# -------------------------------------------------
detection_bp = Blueprint("detection_bp", __name__, url_prefix="/detections")

detection_bp.route("/", methods=["POST"])(create_detection)
detection_bp.route("/my", methods=["GET"])(get_my_detections)
detection_bp.route("/my/<string:detection_type>", methods=["GET"])(get_my_by_type)
detection_bp.route("/my/<int:id>", methods=["GET"])(get_my_single)
detection_bp.route("/my/<int:id>", methods=["PUT"])(update_my_detection)
detection_bp.route("/my/<int:id>", methods=["DELETE"])(delete_my_detection)
detection_bp.route("/my/<string:detection_type>", methods=["DELETE"])(delete_all_my_by_type)
