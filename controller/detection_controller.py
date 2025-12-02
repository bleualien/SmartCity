import os
from flask import Blueprint, request, jsonify, current_app 
from werkzeug.utils import secure_filename 
from models.db import db
from services.detection_service import detect_image_type 
from controller.auth.auth_middleware import token_required
from models.user_model import User
from models.detection import Detection
from datetime import datetime
from sqlalchemy import select 
from sqlalchemy.orm import joinedload, selectinload 

detection_bp = Blueprint('detection_bp', __name__, url_prefix='/detections')

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png','jpg','jpeg','gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@token_required
def create_detection(current_user):
    image = request.files.get('image')
    lat = request.form.get('latitude')
    lon = request.form.get('longitude')
    location = request.form.get('location')
    
    if not image or not lat or not lon or not location:
        return jsonify({'error': 'Missing required fields (image, latitude, longitude, or location)'}), 400
    
    if image.filename == '':
        return jsonify({'error': 'No file selected for upload'}), 400
        
    if not allowed_file(image.filename):
        return jsonify({'error': 'Image file type not allowed'}), 400
        
    try:
        latitude = float(lat)
        longitude = float(lon)
    except ValueError:
        return jsonify({'error': 'Invalid latitude/longitude'}), 400
        
    # 1. Pass the FileStorage object and location data directly to the service
    # 2. Expect four return values: detection_type, result_data, image_name, actual_image_path
    detection_type, result_data, image_name, actual_image_path = detect_image_type(
        image, current_user.id, latitude, longitude, location
    ) 
    
    if detection_type is None:
        # If no detection is found, the service has cleaned up its temporary files.
        return jsonify({'message': 'No pothole or waste detected, file discarded.'}), 200
        
    # The service has already saved the detection to the database.
    # We now just need to ensure the result data has the necessary info for the API response.
    
    # Check if file details were successfully returned (if the file was saved by the service)
    # The check for 'image_name' and 'actual_image_path' is redundant if we trust the service, 
    # but kept for robustness.
    if not image_name or not actual_image_path:
        return jsonify({'error': 'Detection successful, but failed to retrieve saved file path from service.'}), 500

    # The service function `save_to_database` now returns the created Detection object.
    # The current `detect_image_type` implementation returns the `result` dictionary 
    # instead of the Detection object. Let's rely on the dictionary.
    
    # Since the service already saved the data, we update the result_data with user/geo info 
    # and return it. We cannot reliably get the new Detection ID from the current result_data 
    # structure without modifying the service's return value. Assuming the service will add the ID.
    
    # TEMPORARY FIX: Add the new detection's ID to the result_data for response.
    # A better solution is to modify the service to return the Detection model's ID, 
    # but based on the provided service code, the `save_to_database` returns the ID.
    # I will modify the service's return to include the ID in the result_data.
    
    # We must retrieve the newly created detection record to get its ID.
    # The result_data is missing the ID since the service committed the record.
    # We'll use the image_name to retrieve the record, which is brittle but necessary 
    # given the current code structure where the service handles the commit.
    new_detection = Detection.query.filter_by(image_name=image_name, user_id=current_user.id).first()
    
    if not new_detection:
         return jsonify({'error': 'Failed to retrieve newly created detection record.'}), 500
         
    result_data.update({
        "id": new_detection.id, 
        # Latitude, longitude, location are already in result_data from service
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

@token_required
def get_my_detections(current_user):
    records = Detection.query.filter(Detection.user_id == current_user.id).all()
    if not records:
        return jsonify({'message': 'No detections found for this user'}), 200
    return jsonify([r.to_dict() for r in records]), 200

@token_required
def get_my_by_type(current_user, detection_type):
    if detection_type not in ['pothole', 'waste']:
        return jsonify({'error': 'Invalid detection type'}), 400
    records = Detection.query.filter_by(
        user_id=current_user.id, detection_type=detection_type).all()
    return jsonify([r.to_dict() for r in records]), 200

@token_required
def get_my_single(current_user, id): 
    record = Detection.query.filter_by(user_id=current_user.id, id=id).first_or_404()
    return jsonify(record.to_dict()), 200

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
        # Assuming Detection.departments and Detection.tags are relationships
        departments = [dept.department.name for dept in det.departments if hasattr(dept, 'department') and dept.department]
        tags = [tag.tag.name for tag in det.tags if hasattr(tag, 'tag') and tag.tag]
        
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

@token_required
def delete_my_detection(current_user, id):
    record = Detection.query.filter_by(user_id=current_user.id, id=id).first()
    if not record:
        return jsonify({'error': 'Record not found'}), 404
        
    # The image path handling is tricky as the folder is determined by detection type
    # but the path is saved in the record. We rely on the saved paths first.
    
    original_path_to_delete = record.image_path
    annotated_path_to_delete = record.detected_image_path
    
    # Try to delete original image
    if original_path_to_delete and os.path.exists(original_path_to_delete):
        os.remove(original_path_to_delete)
        
    # Try to delete annotated image
    if annotated_path_to_delete and os.path.exists(annotated_path_to_delete):
        os.remove(annotated_path_to_delete)
            
    db.session.delete(record)
    db.session.commit()
    return jsonify({'message': f'{record.detection_type.capitalize()} deleted successfully'}), 200

@token_required
def delete_all_my_by_type(current_user, detection_type):
    if detection_type not in ['pothole', 'waste']:
        return jsonify({'error': 'Invalid detection type'}), 400
        
    records = Detection.query.filter_by(
        user_id=current_user.id, detection_type=detection_type).all()
        
    for record in records:
        original_path_to_delete = record.image_path
        annotated_path_to_delete = record.detected_image_path
        
        # Try to delete original image
        if original_path_to_delete and os.path.exists(original_path_to_delete):
            os.remove(original_path_to_delete)
        
        # Try to delete annotated image
        if annotated_path_to_delete and os.path.exists(annotated_path_to_delete):
            os.remove(annotated_path_to_delete)
                
        db.session.delete(record)
        
    db.session.commit()
    return jsonify({
        "message": f"All {detection_type} records deleted successfully.",
        "count": len(records)
    }), 200