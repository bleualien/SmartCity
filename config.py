import os
import logging

class Config:
    # Secret key for JWT and other security needs
    SECRET_KEY = os.environ.get("SECRET_KEY", "key123")

    # Database configuration
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost:5432/merged_detections'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Base directory
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # Storage directory
    STORAGE_FOLDER = os.path.join(BASE_DIR, 'storage')

    # Pothole folders
    POTHOLE_ORIGINAL_FOLDER = os.path.join(STORAGE_FOLDER, 'pothole', 'original')
    POTHOLE_DETECTED_FOLDER = os.path.join(STORAGE_FOLDER, 'pothole', 'detected')

    # Waste folders
    WASTE_ORIGINAL_FOLDER = os.path.join(STORAGE_FOLDER, 'waste', 'original')
    WASTE_DETECTED_FOLDER = os.path.join(STORAGE_FOLDER, 'waste', 'detected')

    # Annotated folder (general)
    ANNOTATED_FOLDER = os.path.join(STORAGE_FOLDER, 'annotated')

    # Ensure folders exist
    os.makedirs(POTHOLE_ORIGINAL_FOLDER, exist_ok=True)
    os.makedirs(POTHOLE_DETECTED_FOLDER, exist_ok=True)
    os.makedirs(WASTE_ORIGINAL_FOLDER, exist_ok=True)
    os.makedirs(WASTE_DETECTED_FOLDER, exist_ok=True)
    os.makedirs(ANNOTATED_FOLDER, exist_ok=True)


# Logging setup
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
