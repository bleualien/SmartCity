from .db import db

class Tag(db.Model):
    __tablename__ = 'tag'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)

    user = db.relationship('User', back_populates='tags')
    department = db.relationship('Department', back_populates='tags')
    detection_tags = db.relationship('DetectionTag', back_populates='tag', lazy=True)
