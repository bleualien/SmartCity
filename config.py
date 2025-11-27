import os
import logging

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "key123")

    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost:5432/merged_detections'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    STORAGE_FOLDER = os.path.join(BASE_DIR, 'storage')

    POTHOLE_ORIGINAL_FOLDER = os.path.join(STORAGE_FOLDER, 'pothole', 'original')
    POTHOLE_DETECTED_FOLDER = os.path.join(STORAGE_FOLDER, 'pothole', 'detected')

    WASTE_ORIGINAL_FOLDER = os.path.join(STORAGE_FOLDER, 'waste', 'original')
    WASTE_DETECTED_FOLDER = os.path.join(STORAGE_FOLDER, 'waste', 'detected')

    ANNOTATED_FOLDER = os.path.join(STORAGE_FOLDER, 'annotated')
   
    os.makedirs(POTHOLE_ORIGINAL_FOLDER, exist_ok=True)
    os.makedirs(POTHOLE_DETECTED_FOLDER, exist_ok=True)
    os.makedirs(WASTE_ORIGINAL_FOLDER, exist_ok=True)
    os.makedirs(WASTE_DETECTED_FOLDER, exist_ok=True)
    os.makedirs(ANNOTATED_FOLDER, exist_ok=True)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
