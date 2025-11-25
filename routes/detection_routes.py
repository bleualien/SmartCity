# server/routes/detection_routes.py

from flask import Blueprint, request, jsonify
import logging
from services.inference_service import InferenceService
from services.model_loader import ModelLoader
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

# =========================
# ML Detection Blueprint
# =========================
detect_bp = Blueprint("detect", __name__)

# Load models once
model_loader = ModelLoader(
    waste_model_path="runs/detect/waste_yolo_fast/weights/waste.pt",
    pothole_model_path="runs/pothole_yolov8/weights/best.pt"
)
inference = InferenceService(model_loader)


@detect_bp.route("/detect", methods=["POST"])
def detect_route():
    try:
        if "image" not in request.files:
            return jsonify({"success": False, "error": "No file uploaded"}), 400

        file = request.files["image"]
        task = request.form.get("task_type", "waste")

        # Save uploaded file
        saved_path = save_upload(file)

        # Run inference
        result = inference.run(saved_path, task)

        return jsonify(result), 200 if result["success"] else 500

    except Exception as e:
        logger.exception("Detection API error")
        return jsonify({"success": False, "error": str(e)}), 500


# =========================
# DB/User Detection Blueprint
# =========================
detection_bp = Blueprint("detection_bp", __name__, url_prefix="/detections")

# Database/User Routes
detection_bp.route("/", methods=["POST"])(create_detection)
detection_bp.route("/my", methods=["GET"])(get_my_detections)
detection_bp.route("/my/<string:detection_type>", methods=["GET"])(get_my_by_type)
detection_bp.route("/my/<int:id>", methods=["GET"])(get_my_single)
detection_bp.route("/my/<int:id>", methods=["PUT"])(update_my_detection)
detection_bp.route("/my/<int:id>", methods=["DELETE"])(delete_my_detection)
detection_bp.route("/my/<string:detection_type>", methods=["DELETE"])(delete_all_my_by_type)
