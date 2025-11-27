from flask import Blueprint, request, jsonify
import logging
import os

from utils.file_utils import save_upload
from services.inference_service import InferenceService
from model_loader import ModelLoader       

model_loader = ModelLoader(
    waste_model_path="runs/detect/waste_yolo_fast/weights/waste.pt",
    pothole_model_path="runs/pothole_yolov8/weights/best.pt"
)

inference_service = InferenceService(model_loader)

logger = logging.getLogger(__name__)
detect_bp = Blueprint("detect", __name__)


@detect_bp.route("/detect", methods=["POST"])
def detect():
    try:
        user_id = request.form.get("user_id", None)
        task_type = request.form.get("task_type", "waste")

        # Case 1: User uploaded image
        if "image" in request.files:
            image = request.files["image"]
            saved_path = save_upload(image)

            result = inference_service.run(
                image_path=saved_path,
                user_id=user_id,
                task_type=task_type
            )

            return jsonify({
                "success": True,
                "detection_type": result.get("task_type"),
                "result": result
            }), 200

        # Case 2: Image path already on server
        image_path = request.form.get("image_path")

        if image_path:
            if not os.path.exists(image_path):
                return jsonify({"success": False, "error": "File not found"}), 404

            result = inference_service.run(
                image_path=image_path,
                user_id=user_id,
                task_type=task_type
            )

            return jsonify({
                "success": True,
                "detection_type": result.get("task_type"),
                "result": result
            }), 200

        return jsonify({"success": False, "error": "No image provided"}), 400

    except Exception as e:
        logger.exception("Detection API error")
        return jsonify({"success": False, "error": str(e)}), 500
