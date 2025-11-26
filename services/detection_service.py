import os
import time
from datetime import datetime
from flask import current_app

# Models & DB
from models import db, Detection, Image, Tag, DetectionTag

from services.model_loader__old import ModelLoader
from utils.viz import annotate_and_save_ultralytics
from reasoning.kg_gnn import KnowledgeGraphReasoner
from processors.waste_processor import WasteProcessor
from processors.pothole_processor import PotholeProcessor

# Singletons
kg = KnowledgeGraphReasoner()
WASTE_PROCESSOR = WasteProcessor()
POTHOLE_PROCESSOR = PotholeProcessor()

MODEL_LOADER = ModelLoader(
    waste_model_path="runs/detect/waste_yolo_fast/weights/waste.pt",
    pothole_model_path="runs/pothole_yolov8/weights/best.pt"
)

POTHOLE_MODEL = MODEL_LOADER.pothole_model
WASTE_MODEL = MODEL_LOADER.waste_model


def _normalize_user_id(uid):
    """Ensure FK does not break. Convert invalid IDs to None."""
    try:
        uid_int = int(uid)
        return uid_int if uid_int > 0 else None
    except:
        return None


def save_to_database(detection_type, result, user_id=0):

    # Always ensure a valid user_id (FK)
    normalized_user_id = _normalize_user_id(result.get("user_id"))
    if normalized_user_id is None:
        normalized_user_id = 1  # fallback system/admin user

    detection_payload = {
        "user_id": normalized_user_id,
        "detection_type": detection_type,
        "image_name": result.get("image_name") or "",

        "latitude": result.get("latitude") or 0.0,
        "longitude": result.get("longitude") or 0.0,
        "location": result.get("location") or "",

        "pothole_severity": result.get("pothole_severity"),
        "waste_category": result.get("waste_category"),
        "department": result.get("department") or "Unknown",
        "detection_status": result.get("detection_status") or ""
    }

    payload = {k: v for k, v in detection_payload.items() if v is not None}

    detection = Detection(**payload)
    db.session.add(detection)
    db.session.flush()

    # Save image rows
    annotated = result.get("annotated_name")
    if annotated:
        image_row = Image(
            detection_id=detection.id,
            uploaded_filename=result.get("image_name") or "",
            annotated_filename=annotated,
            timestamp=datetime.utcnow()
        )
        db.session.add(image_row)

    # Save tags for waste
    waste_cat = result.get("waste_category")
    if waste_cat:
        tag = Tag.query.filter_by(name=waste_cat).first()
        if tag:
            try:
                dt = DetectionTag(detection_id=detection.id, tag_id=tag.id)
                db.session.add(dt)
            except:
                try:
                    detection.tags.append(tag)
                except:
                    pass

    db.session.commit()
    return detection.id


def detect_image_type(image, user_id):

    if not POTHOLE_MODEL or not WASTE_MODEL:
        return None, None

    timestamp = int(time.time())
    original_filename = f"{timestamp}_{image.filename}"
    uid = str(timestamp)

    temp_path = os.path.join(
        current_app.config['STORAGE_FOLDER'],
        f"temp_{original_filename}"
    )
    image.save(temp_path)

    # ----------------------------------------------------------------------
    # POTHOLE DETECTION
    # ----------------------------------------------------------------------
    pothole_results = POTHOLE_MODEL.predict(source=temp_path, conf=0.5)
    if pothole_results and len(getattr(pothole_results[0], "boxes", [])) > 0:

        image.save(os.path.join(current_app.config['POTHOLE_ORIGINAL_FOLDER'], original_filename))

        annotated_filename = annotate_and_save_ultralytics(
            pothole_results,
            temp_path,
            current_app.config['POTHOLE_DETECTED_FOLDER'],
            uid
        )

        pothole_info = POTHOLE_PROCESSOR.extract(temp_path, pothole_results)
        primary = pothole_info.get("primary") or {}

        # Reasoning result
        record = {"type": "pothole", "params": pothole_info}
        scores = kg.reason(record)
        department = max(scores, key=scores.get)

        result = {
            "user_id": user_id,
            "image_name": original_filename,
            "annotated_name": annotated_filename,

            "pothole_severity": primary.get("class_name") or "unknown",
            "waste_category": None,
            "detection_status": f"{primary.get('class_name', 'pothole')} detected",

            "department": department,
            "area_pct": primary.get("area_pct"),
            "est_depth_m": primary.get("est_depth_m")
        }

        os.remove(temp_path)
        save_to_database("pothole", result)
        return "pothole", result

    # ----------------------------------------------------------------------
    # WASTE DETECTION
    # ----------------------------------------------------------------------
    waste_results = WASTE_MODEL.predict(source=temp_path, conf=0.5)
    if waste_results and len(getattr(waste_results[0], "boxes", [])) > 0:

        image.save(os.path.join(current_app.config['WASTE_ORIGINAL_FOLDER'], original_filename))

        annotated_filename = annotate_and_save_ultralytics(
            waste_results,
            temp_path,
            current_app.config['WASTE_DETECTED_FOLDER'],
            uid
        )

        waste_info = WASTE_PROCESSOR.extract(temp_path, waste_results)
        primary = waste_info.get("primary") or {}

        category = primary.get("class_name") or "Unknown"

        record = {"type": "waste", "params": waste_info}
        scores = kg.reason(record)
        department = max(scores, key=scores.get)

        result = {
            "user_id": user_id,
            "image_name": original_filename,
            "annotated_name": annotated_filename,

            "pothole_severity": None,
            "waste_category": category,
            "detection_status": f"{category} detected",

            "department": department,
            "area_pct": primary.get("area_pct")
        }

        os.remove(temp_path)
        save_to_database("waste", result)
        return "waste", result

    # ----------------------------------------------------------------------
    # NO DETECTION
    # ----------------------------------------------------------------------
    os.remove(temp_path)

    result = {
        "user_id": user_id,
        "image_name": None,
        "annotated_name": None,
        "pothole_severity": None,
        "waste_category": None,
        "detection_status": "No detection",
        "department": None
    }

    save_to_database("none", result)
    return None, result
