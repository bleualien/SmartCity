from .db import db

class Tag(db.Model):
    __tablename__ = 'tag'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

    # department_id MUST BE OPTIONAL
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    user = db.relationship('User', back_populates='tags')
    department = db.relationship('Department', back_populates='tags')

    detection_tags = db.relationship('DetectionTag', back_populates='tag', lazy=True)
