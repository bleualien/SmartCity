import os
import sys
from flask import Flask

from config import Config, setup_logging
from flask_cors import CORS
from models.db import db, migrate

# IMPORT CORRECT BLUEPRINTS
from routes.detection_routes import detection_bp, detect_ml_bp
from routes.detect import detect_bp
from controller.auth.auth_controller import auth_bp

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def create_app():
    app = Flask(__name__)
    CORS(app)

    # Load config
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # REGISTER BLUEPRINTS (correct order, correct names)
    app.register_blueprint(detection_bp, url_prefix="/api/detections")          # /api/detections/...
    app.register_blueprint(detect_ml_bp, url_prefix="/detection")    # /detection/detects
    # app.register_blueprint(detect_bp, url_prefix="/detect")          # old detect route
    app.register_blueprint(auth_bp)

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)