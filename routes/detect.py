# server/routes/detect.py
from flask import Blueprint, request, jsonify
import logging
from services.inference_service import InferenceService
from services.model_loader import ModelLoader
from utils.file_utils import save_upload
import os

logger = logging.getLogger(__name__)
detect_bp = Blueprint("detect", __name__)

# Load models once
model_loader = ModelLoader(
    waste_model_path="runs/detect/waste_yolo_fast/weights/waste.pt",
    pothole_model_path="runs/pothole_yolov8/weights/best.pt"
)

inference = InferenceService(model_loader)


@detect_bp.route("/detect", methods=["POST"])
def detect():
    try:
        task = request.form.get("task_type", "waste")

        # ---------------------------
        # CASE 1: User uploads an image
        # ---------------------------
        if "image" in request.files:
            file = request.files["image"]
            saved_path = save_upload(file)
            result = inference.run(saved_path, task)
            return jsonify(result), 200

        # ---------------------------
        # CASE 2: User passes image_path
        # (example: storage/waste/detected/abc.jpg)
        # ---------------------------
        image_path = request.form.get("image_path")

        if image_path:
            if not os.path.exists(image_path):
                return jsonify({"success": False, "error": "File not found on server"}), 404

            result = inference.run(image_path, task)
            return jsonify(result), 200

        # ---------------------------
        # No file or path provided
        # ---------------------------
        return jsonify({"success": False, "error": "No file or image_path provided"}), 400

    except Exception as e:
        logger.exception("Detection API error")
        return jsonify({"success": False, "error": str(e)}), 500
