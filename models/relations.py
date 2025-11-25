import uuid
from .db import db

class DetectionDepartment(db.Model):
    __tablename__ = 'detection_department'

    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    detection_id = db.Column(db.Integer, db.ForeignKey('detections.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)

    detection = db.relationship("Detection", back_populates="departments")
    department = db.relationship("Department", back_populates="detection_departments")


class DetectionTag(db.Model):
    __tablename__ = 'detection_tag'

    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    detection_id = db.Column(db.Integer, db.ForeignKey('detections.id'))
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'))

    detection = db.relationship('Detection', back_populates='tags')
    tag = db.relationship('Tag', back_populates='detection_tags')
