import os
import shutil
from ultralytics import YOLO
from deepface import DeepFace
from PIL import Image


import cv2

# -------------------------------
# 🔧 Helper: Load YOLO model
# -------------------------------
def _load_yolo_model(model_path: str = None):
    if model_path is None:
        possible_paths = [
            "best.pt",
            "Main/best.pt",
            "beta-testing/best.pt"
        ]

        for path in possible_paths:
            if os.path.exists(path):
                model_path = path
                break

    if model_path is None:
        raise FileNotFoundError("YOLO model (best.pt) not found")

    return YOLO(model_path)


# -------------------------------
# 1️⃣ Extract face (Generic)
# -------------------------------
def extract_face(image_path: str, face_type: str, model_path: str = None):
    """
    Extract face from image using YOLO.
    face_type = "id" or "live"
    Returns saved face image path or None
    """

    model = _load_yolo_model(model_path)

    results = model.predict(image_path)[0]
    image = Image.open(image_path)

    temp_dir = "temp_faces"
    os.makedirs(temp_dir, exist_ok=True)

    if not hasattr(results, "boxes") or len(results.boxes.xyxy) == 0:
        return None

    # First detected face
    x1, y1, x2, y2 = map(int, results.boxes.xyxy[0])
    face_img = image.crop((x1, y1, x2, y2))

    face_path = os.path.join(temp_dir, f"{face_type}_face.jpg")
    face_img.save(face_path)

    return face_path



# 1️⃣ BACKWARD COMPATIBILITY

def extract_face_from_id_card(id_card_path: str, model_path: str = None):
    """
    Old function name support.
    Internally uses extract_face()
    """
    return extract_face(
        image_path=id_card_path,
        face_type="id",
        model_path=model_path
    )


# -------------------------------
# 2️⃣ Compare two faces (ArcFace)
# -------------------------------
def compare_faces(face1_path: str, face2_path: str):
    """
    Compare two faces using ArcFace
    Returns (is_match, distance)
    """

    result = DeepFace.verify(
        img1_path=face1_path,
        img2_path=face2_path,
        model_name="ArcFace",
        enforce_detection=True,
        distance_metric="cosine"
    )

    distance = result["distance"]
    # 🔒 ArcFace threshold (lower distance = more similar)
    # Threshold of 0.50 is optimal for ArcFace with cosine distance
    is_match = distance < 0.50

    return is_match, distance



def capture_live_image(save_path: str = "uploads/live.jpg", timeout: int = 10):
    """
    Opens webcam, auto-detects face, auto-captures image.
    timeout = seconds
    """

    os.makedirs("uploads", exist_ok=True)

    cam = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    start_time = cv2.getTickCount()
    freq = cv2.getTickFrequency()

    while True:
        ret, frame = cam.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        # ✅ exactly one face → auto capture
        if len(faces) == 1:
            cv2.imwrite(save_path, frame)
            break

        elapsed = (cv2.getTickCount() - start_time) / freq
        if elapsed > timeout:
            cam.release()
            cv2.destroyAllWindows()
            return None

    cam.release()
    cv2.destroyAllWindows()
    return save_path
