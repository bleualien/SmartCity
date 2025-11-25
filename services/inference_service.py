from flask import current_app
import time
from utils.viz import annotate_and_save_ultralytics

class InferenceService:
    def __init__(self, model_loader):
        self.model_loader = model_loader

    def run(self, image_path, task_type="waste"):
        start = time.time()
        try:
            results = self.model_loader.predict(image_path, task_type)
            detections = []

            for box in results[0].boxes:
                detections.append({
                    "bbox": box.xyxy.tolist()[0],
                    "confidence": float(box.conf[0]),
                    "class_id": int(box.cls[0])
                })

            # Generate unique UID for this image
            uid = str(int(time.time()))
            # Use a configured annotated folder
            annotated_dir = current_app.config['ANNOTATED_FOLDER']

            # Pass all 4 required arguments
            annotated_path = annotate_and_save_ultralytics(results, image_path, annotated_dir, uid)

            return {
                "success": True,
                "task_type": task_type,
                "detections": detections,
                "annotated_path": annotated_path,
                "execution_time": round(time.time() - start, 3)
            }

        except Exception as e:
            return {
                "success": False,
                "task_type": task_type,
                "error": str(e)
            }
