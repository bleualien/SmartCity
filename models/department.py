from .db import db

class Department(db.Model):
    __tablename__ = 'department'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    tags = db.relationship('Tag', back_populates='department', lazy=True)
    detection_departments = db.relationship('DetectionDepartment', back_populates='department', lazy=True)
