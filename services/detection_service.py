import os
import time
from flask import current_app
from services.model_loader import ModelLoader
from utils.viz import annotate_and_save_ultralytics
from reasoning.kg_gnn import KnowledgeGraphReasoner   # <-- FIXED IMPORT
from processors.waste_processor import WasteProcessor
from processors.pothole_processor import PotholeProcessor


# Initialize KGNN (only once)
kg = KnowledgeGraphReasoner()

WASTE_PROCESSOR = WasteProcessor()
POTHOLE_PROCESSOR = PotholeProcessor()


# Initialize YOLO models
MODEL_LOADER = ModelLoader(
    waste_model_path="runs/detect/waste_yolo_fast/weights/waste.pt",
    pothole_model_path="runs/pothole_yolov8/weights/best.pt"
)

POTHOLE_MODEL = MODEL_LOADER.pothole_model
WASTE_MODEL = MODEL_LOADER.waste_model

CLASS_MAP = {0: 'Glass', 1: 'Metal', 2: 'Paper', 3: 'Plastic', 4: 'Residual'}


def detect_image_type(image):
    """
    Detects whether the uploaded image contains a pothole or waste.
    Annotates images and saves them in appropriate folders.
    Applies KGNN to determine the responsible department dynamically.
    Returns (detection_type, result_data)
    """
    if not POTHOLE_MODEL or not WASTE_MODEL:
        return None, None

    timestamp = int(time.time())
    original_filename = f"{timestamp}_{image.filename}"
    uid = str(timestamp)

    temp_path = os.path.join(current_app.config['STORAGE_FOLDER'], f"temp_{original_filename}")
    image.save(temp_path)

    # =====================================================
    # -------------- POTHOLE DETECTION --------------------
    # =====================================================
    pothole_results = POTHOLE_MODEL.predict(source=temp_path, conf=0.5)

    if len(pothole_results[0].boxes) > 0:

        # Save Original
        pothole_original_path = os.path.join(current_app.config['POTHOLE_ORIGINAL_FOLDER'], original_filename)
        image.save(pothole_original_path)

        # Annotate
        annotated_dir = current_app.config['POTHOLE_DETECTED_FOLDER']
        annotated_filename = annotate_and_save_ultralytics(pothole_results, temp_path, annotated_dir, uid)

        # Extract severity class (ex: "severe_large")
        class_name = pothole_results[0].names[int(pothole_results[0].boxes.cls[0].item())]
        pothole_severity = class_name.split('_')[0]

        # ---------- KGNN REASONING ----------
        record = {
            "type": "pothole",
            "params": {
                "primary": {
                    "area_pct": 0.03,        # If you want, replace with real calculation
                    "est_depth_m": 0.12,     # Replace with real calculation
                    "class_name": class_name
                }
            }
        }

        scores = kg.reason(record)
        department = max(scores, key=scores.get)

        os.remove(temp_path)

        return "pothole", {
            "image_name": original_filename,
            "annotated_name": annotated_filename,
            "pothole_severity": pothole_severity,
            "waste_category": None,
            "detection_status": f"{pothole_severity} pothole detected",
            "department": department     # <-- DYNAMIC DEPARTMENT
        }

    # =====================================================
    # -------------- WASTE DETECTION ----------------------
    # =====================================================
    waste_results = WASTE_MODEL.predict(source=temp_path, conf=0.5)

    if len(waste_results[0].boxes) > 0:

        waste_original_path = os.path.join(current_app.config['WASTE_ORIGINAL_FOLDER'], original_filename)
        image.save(waste_original_path)

        annotated_dir = current_app.config['WASTE_DETECTED_FOLDER']
        annotated_filename = annotate_and_save_ultralytics(waste_results, temp_path, annotated_dir, uid)

        first_class = int(waste_results[0].boxes.cls[0].item())
        category = CLASS_MAP.get(first_class, "Unknown")

        # ---------- KGNN REASONING ----------
        record = {
            "type": "waste",
            "params": {
                "primary": {
                    "class_name": category
                }
            }
        }

        scores = kg.reason(record)
        department = max(scores, key=scores.get)

        os.remove(temp_path)

        return "waste", {
            "image_name": original_filename,
            "annotated_name": annotated_filename,
            "pothole_severity": None,
            "waste_category": category,
            "detection_status": f"{category} detected",
            "department": department     # <-- DYNAMIC DEPARTMENT
        }

    # =====================================================
    # ------------- NO DETECTION CASE ---------------------
    # =====================================================
    os.remove(temp_path)

    return None, {
        "image_name": None,
        "annotated_name": None,
        "pothole_severity": None,
        "waste_category": None,
        "detection_status": "No detection",
        "department": None
    }
