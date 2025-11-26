import os
from flask import Blueprint, request, jsonify, current_app
from models.db import db
from services.detection_service import detect_image_type
from controller.auth.auth_middleware import token_required
from models.user_model import User 
from models.detection import Detection
from datetime import datetime

detection_bp = Blueprint('detection_bp', __name__, url_prefix='/detections')


# POST — Detect and Save
@detection_bp.route('/', methods=['POST'])
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

    
    result_data["latitude"] = latitude
    result_data["longitude"] = longitude
    result_data["location"] = location

    # Construct paths for already uploaded images
    image_name = image.filename
    image_path = f"uploads/{detection_type}/{image_name}"
    if detection_type == 'pothole':
        detected_image_path = f"storage/pothole/detected/{image_name}"
    else:
        detected_image_path = f"storage/waste/detected/{image_name}"


   
    return jsonify({
        'message': f'{detection_type.capitalize()} detected successfully.',
        'data': result_data
    }), 201



#  GET — All detections(current user detections only)
@detection_bp.route('/my', methods=['GET'])
@token_required
def get_my_detections(current_user):
    records = Detection.query.filter(Detection.user_id == current_user.id).all()

    if not records:
        return jsonify({'message': 'No detections found for this user'}), 200

    return jsonify([r.to_dict() for r in records]), 200

#  GET — All by type(like pthole/waste) for current user
@detection_bp.route('/my/<string:detection_type>', methods=['GET'])
@token_required
def get_my_by_type(current_user, detection_type):
    if detection_type not in ['pothole', 'waste']:
        return jsonify({'error': 'Invalid detection type'}), 400

    records = Detection.query.filter_by(
        user_id=current_user.id, detection_type=detection_type).all()
    return jsonify([r.to_dict() for r in records]), 200


#  GET — single detection by id of the image for current user

@detection_bp.route('/me/<int:id>', methods=['GET'])
@token_required
def get_my_single(current_user, id):
    record = Detection.query.filter_by(user_id=current_user.id, id=id).first_or_404()
    print("hi")
    return jsonify(record.to_dict()), 200


# PUT — Update detection (user can update only location)
@detection_bp.route('/my/<int:id>', methods=['PUT'])
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

    return jsonify({'message': f'{record.detection_type.capitalize()} location updated',
                    'data': record.to_dict()}), 200


# DELETE SINGLE — by ID for current user
@detection_bp.route('/my/<int:id>', methods=['DELETE'])
@token_required
def delete_my_detection(current_user, id):
    record = Detection.query.filter_by(user_id=current_user.id, id=id).first()
    if not record:
        return jsonify({'error': 'Record not found'}), 404

    # Remove stored image from disk
    folder = current_app.config.get('DETECTION_IMAGE_FOLDER')
    if folder and record.image_name:
        image_path = os.path.join(folder, record.image_name)
        if os.path.exists(image_path):
            os.remove(image_path)

    db.session.delete(record)
    db.session.commit()

    return jsonify({'message': f'{record.detection_type.capitalize()} deleted successfully'}), 200


# DELETE ALL — by type for current user
@detection_bp.route('/my/<string:detection_type>', methods=['DELETE'])
@token_required
def delete_all_my_by_type(current_user, detection_type):
    if detection_type not in ['pothole', 'waste']:
        return jsonify({'error': 'Invalid detection type'}), 400

    records = Detection.query.filter_by(
        user_id=current_user.id, detection_type=detection_type).all()

    folder = current_app.config.get('DETECTION_IMAGE_FOLDER')

    for record in records:
        # Remove stored image from disk
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