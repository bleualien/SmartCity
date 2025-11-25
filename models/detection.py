from datetime import datetime
from .db import db

class Detection(db.Model):
    __tablename__ = "detections"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    detection_type = db.Column(db.String(20), nullable=False)  # pothole / waste
    image_name = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    pothole_severity = db.Column(db.String(20), nullable=True)
    waste_category = db.Column(db.String(50), nullable=True)
    department = db.Column(db.String(100), nullable=False)
    detection_status = db.Column(db.String(50), nullable=False)

    # Relationships
    user = db.relationship("User", back_populates='detections')
    images = db.relationship('Image', back_populates='detection', lazy=True)
    departments = db.relationship('DetectionDepartment', back_populates='detection', lazy=True)
    tags = db.relationship('DetectionTag', back_populates='detection', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "image_name": self.image_name,
            "detection_type": self.detection_type,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "location": self.location,
            "pothole_severity": self.pothole_severity,
            "waste_category": self.waste_category,
            "department": self.department,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "detection_status": self.detection_status
        }
