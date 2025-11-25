from .db import db

class Image(db.Model):
    __tablename__ = 'image'

    id = db.Column(db.Integer, primary_key=True)
    detection_id = db.Column(db.Integer, db.ForeignKey('detections.id'))
    uploaded_filename = db.Column(db.String, nullable=False)
    annotated_filename = db.Column(db.String, nullable=True)
    timestamp = db.Column(db.DateTime, default=db.func.now())

    detection = db.relationship('Detection', back_populates='images')
