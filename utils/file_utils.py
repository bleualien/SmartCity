import os
import json
import shutil
from werkzeug.utils import secure_filename
from datetime import datetime
from PIL import Image
import numpy as np

# =========================
# BASIC CONSTANTS
# =========================

ALLOWED_EXT = {'png', 'jpg', 'jpeg'}
BASE_STORAGE = os.path.join(os.getcwd(), "storage")
UPLOAD_FOLDER = os.path.join(BASE_STORAGE, "uploads")


# =========================
# CORE UTILITIES
# =========================

def ensure_dirs(base_dir=BASE_STORAGE):
    """
    Ensure standard project directories exist:
    - storage/uploads
    - storage/annotated
    - storage/params
    - storage/departments/waste
    - storage/departments/pothole
    """
    paths = [
        base_dir,
        os.path.join(base_dir, 'uploads'),
        os.path.join(base_dir, 'annotated'),
        os.path.join(base_dir, 'params'),
        os.path.join(base_dir, 'departments', 'waste'),
        os.path.join(base_dir, 'departments', 'pothole')
    ]
    for p in paths:
        os.makedirs(p, exist_ok=True)
    return paths


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def secure_name(filename: str) -> str:
    return secure_filename(filename)


def now_str() -> str:
    return datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')


# =========================
# ✅ REQUIRED FIXED FUNCTION
# =========================

def save_upload(file):
    """
    Save uploaded file and return full file path.
    """
    ensure_dirs()

    if not file or file.filename == '':
        raise ValueError("No file provided")

    if not allowed_file(file.filename):
        raise ValueError("File type not allowed")

    filename = f"{now_str()}_{secure_name(file.filename)}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    file.save(filepath)
    return filepath


# =========================
# JSON Utilities
# =========================

def save_json(path: str, obj):
    """Save a Python object (dict) as formatted JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)


def load_image_as_bgr_array(path: str):
    """Load image (via PIL) and convert to OpenCV-style BGR numpy array."""
    img = Image.open(path).convert('RGB')
    arr = np.array(img)[:, :, ::-1].copy()  # RGB → BGR
    return arr


# =========================
# DEPARTMENT STORAGE SYSTEM
# =========================

def ensure_dir(path):
    """Safely create a directory if it doesn’t exist."""
    os.makedirs(path, exist_ok=True)
    return path


def save_to_department(task_type, departments, annotated_path, params_path):
    """
    Save annotated image + params JSON into department-specific folders.

    Folder structure:
    storage/
        departments/
            waste/
            pothole/
    """

    base_dir = os.path.join('storage', 'departments', task_type.lower())
    ensure_dir(base_dir)

    for dept in departments:
        safe_dept = dept.replace(" ", "_")
        dept_dir = ensure_dir(os.path.join(base_dir, safe_dept))

        # Copy annotated image
        if os.path.exists(annotated_path):
            shutil.copy2(annotated_path, dept_dir)

        # Copy parameters JSON
        if os.path.exists(params_path):
            shutil.copy2(params_path, dept_dir)

    print(f"✅ Files stored under {task_type} department folders: {', '.join(departments)}")
