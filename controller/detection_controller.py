import os
from flask import Blueprint, request, jsonify, current_app 
from models.db import db
from services.detection_service import detect_image_type
from controller.auth.auth_middleware import token_required
from models.user_model import User
from models.detection import Detection
from datetime import datetime
from sqlalchemy import select 
from sqlalchemy.orm import joinedload, selectinload 

detection_bp = Blueprint('detection_bp', __name__, url_prefix='/detections')

# POST 
@token_required
def create_detection(current_user):
    image = request.files.get('image')
    lat = request.form.get('latitude')
    lon = request.form.get('longitude')
    location = request.form.get('location')
    if not image or not lat or not lon or not location:
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        latitude = float(lat)
        longitude = float(lon)
    except ValueError:
        return jsonify({'error': 'Invalid latitude/longitude'}), 400
    detection_type, result_data = detect_image_type(image, current_user.id)
    if detection_type is None:
        return jsonify({'message': 'No pothole or waste detected!'}), 200
    image_name = image.filename    
    department_default = current_app.config.get("DEFAULT_DEPARTMENT", "General")
    status_default = current_app.config.get("DEFAULT_DETECTION_STATUS", "Pending")
    new_detection = Detection(
        user_id=current_user.id,
        detection_type=detection_type,
        image_name=image_name,
        latitude=latitude,
        longitude=longitude,
        location=location,
        department=department_default,
        detection_status=status_default
    )
    db.session.add(new_detection)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    result_data.update({
        "latitude": latitude,
        "longitude": longitude,
        "location": location,
        "user": {
            "id": current_user.id,
            "name": getattr(current_user, 'name', None),
            "email": current_user.email,
            "role": getattr(current_user, 'role', None),
            "organization_name": getattr(current_user, 'organization_name', None)
        }
    })

    return jsonify({
        'message': f'{detection_type.capitalize()} detected successfully.',
        'data': result_data
    }), 201

# GET 
@token_required
def get_my_detections(current_user):
    records = Detection.query.filter(Detection.user_id == current_user.id).all()
    if not records:
        return jsonify({'message': 'No detections found for this user'}), 200
    return jsonify([r.to_dict() for r in records]), 200

# GET 
@token_required
def get_my_by_type(current_user, detection_type):
    if detection_type not in ['pothole', 'waste']:
        return jsonify({'error': 'Invalid detection type'}), 400
    records = Detection.query.filter_by(
        user_id=current_user.id, detection_type=detection_type).all()
    return jsonify([r.to_dict() for r in records]), 200

# GET 
@token_required
def get_my_single(current_user, id):
    record = Detection.query.filter_by(user_id=current_user.id, id=id).first_or_404()
    return jsonify(record.to_dict()), 200

# GET 
@token_required
def get_detections_by_user(current_user, user_id):
    stmt = (
        select(Detection)
        .where(Detection.user_id == user_id)
        .options(joinedload(Detection.user)) 
        .order_by(Detection.timestamp.desc())
    )
    records = db.session.execute(stmt).scalars().all() 
    if not records:
        return jsonify({"message": "No detections found for this user"}), 404
    data = []
    for det in records:
        user = det.user        
        det_dict = {
            "id": det.id,
            "detection_type": det.detection_type,
            "image_name": det.image_name,
            "latitude": det.latitude,
            "longitude": det.longitude,
            "location": det.location,
            "user": {
                "id": user.id,
                "name": getattr(user, 'name', None),
                "email": user.email,
                "role": getattr(user, 'role', None),
                "organization_name": getattr(user, 'organization_name', None)
            }
        }
        data.append(det_dict)

    return jsonify({"detections": data}), 200

# GET 
@token_required
def get_user_full_details(current_user, user_id):
    if getattr(current_user, "role", "user") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    user = (
        User.query.options(
            joinedload(User.detections)
            .joinedload(Detection.departments)
            .joinedload("department"),
            joinedload(User.detections)
            .joinedload(Detection.tags)
            .joinedload("tag")
        )
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        return jsonify({"error": "User not found"}), 404
    data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "organization_name": user.organization_name,
        "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": user.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        "detections": []
    }
    for det in user.detections:
        departments = [dept.department.name for dept in det.departments]
        tags = [tag.tag.name for tag in det.tags]
        data["detections"].append({
            "id": det.id,
            "detection_type": det.detection_type,
            "image_name": det.image_name,
            "latitude": det.latitude,
            "longitude": det.longitude,
            "location": det.location,
            "timestamp": det.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "detection_status": det.detection_status,
            "departments": departments,
            "tags": tags
        })

    return jsonify(data), 200

# PUT 
@token_required
def update_my_detection(current_user, id):
    data = request.json
    new_location = data.get('location')
    if not new_location:
        return jsonify({'error': 'Location is required'}), 400
    record = Detection.query.filter_by(user_id=current_user.id, id=id).first()
    if not record:
        return jsonify({'error': 'Record not found'}), 404
    record.location = new_location
    db.session.commit()
    return jsonify({
        'message': f'{record.detection_type.capitalize()} location updated',
        'data': record.to_dict()
    }), 200

# DELETE SINGLE 
@token_required
def delete_my_detection(current_user, id):
    record = Detection.query.filter_by(user_id=current_user.id, id=id).first()
    if not record:
        return jsonify({'error': 'Record not found'}), 404
    folder = current_app.config.get('DETECTION_IMAGE_FOLDER')
    if folder and record.image_name:
        image_path = os.path.join(folder, record.image_name)
        if os.path.exists(image_path):
            os.remove(image_path)
    db.session.delete(record)
    db.session.commit()
    return jsonify({'message': f'{record.detection_type.capitalize()} deleted successfully'}), 200

# DELETE ALL 
def delete_all_my_by_type(current_user, detection_type):
    if detection_type not in ['pothole', 'waste']:
        return jsonify({'error': 'Invalid detection type'}), 400
    records = Detection.query.filter_by(
        user_id=current_user.id, detection_type=detection_type).all()
    folder = current_app.config.get('DETECTION_IMAGE_FOLDER')
    for record in records:
        if folder and record.image_name:
            image_path = os.path.join(folder, record.image_name)
            if os.path.exists(image_path):
                os.remove(image_path)
        db.session.delete(record)
    db.session.commit()
    return jsonify({
        "message": f"All {detection_type} records deleted successfully.",
        "count": len(records)
    }), 200