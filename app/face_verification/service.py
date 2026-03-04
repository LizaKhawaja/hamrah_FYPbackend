# import os
# import cv2
# from ultralytics import YOLO
# from deepface import DeepFace
# from PIL import Image

# # 🔧 Helper: Load YOLO model
# def _load_yolo_model(model_path: str = None):
#     if model_path is None:
#         possible_paths = [
#             "best.pt",
#             "Main/best.pt",
#             "beta-testing/best.pt"
#         ]

#         for path in possible_paths:
#             if os.path.exists(path):
#                 model_path = path
#                 break

#     if model_path is None:
#         raise FileNotFoundError("YOLO model (best.pt) not found")

#     return YOLO(model_path)


# #  LOAD MODELS ONCE (IMPORTANT)

# yolo_model = _load_yolo_model()
# DeepFace.build_model("ArcFace")


# #  Extract face
# def extract_face(image_path: str, face_type: str):
#     """
#     Extract face from image using YOLO.
#     Returns saved face image path or None
#     """

#     results = yolo_model.predict(image_path)[0]
#     image = Image.open(image_path)

#     temp_dir = "temp_faces"
#     os.makedirs(temp_dir, exist_ok=True)

#     if not hasattr(results, "boxes") or len(results.boxes.xyxy) == 0:
#         return None

#     x1, y1, x2, y2 = map(int, results.boxes.xyxy[0])
#     face_img = image.crop((x1, y1, x2, y2))

#     face_path = os.path.join(temp_dir, f"{face_type}_face.jpg")
#     face_img.save(face_path)

#     return face_path



# #  BACKWARD COMPATIBILITY
# def extract_face_from_id_card(id_card_path: str):
#     return extract_face(
#         image_path=id_card_path,
#         face_type="id"
#     )



# #  Compare faces (ArcFace)
# def compare_faces(face1_path: str, face2_path: str):

#     result = DeepFace.verify(
#         img1_path=face1_path,
#         img2_path=face2_path,
#         model_name="ArcFace",
#         enforce_detection=True,
#         distance_metric="cosine"
#     )

#     distance = result["distance"]
#     is_match = distance < 0.60

#     return is_match, distance

# #  DUPLICATE FACE CHECK
# def check_duplicate_face(new_face_path: str, db):
#     """
#     Check if this face already exists in database.
#     Returns True if duplicate found.
#     """

#     from app import models  # prevent circular import

#     existing_drivers = db.query(models.User).filter(
#         models.User.role == "driver"
#     ).all()

#     for user in existing_drivers:

#         if not user.nic_image_url:
#             continue

#         try:
#             stored_face = extract_face(user.nic_image_url, face_type="stored")

#             if not stored_face:
#                 continue

#             is_match, distance = compare_faces(stored_face, new_face_path)

#             if is_match:
#                 print("Duplicate face detected. Distance:", distance)
#                 return True

#         except Exception:
#             continue

#     return False



# #  Capture Live Image
# def capture_live_image(save_path: str = "uploads/live.jpg", timeout: int = 10):

#     os.makedirs("uploads", exist_ok=True)

#     cam = cv2.VideoCapture(0)
#     face_cascade = cv2.CascadeClassifier(
#         cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
#     )

#     start_time = cv2.getTickCount()
#     freq = cv2.getTickFrequency()

#     while True:
#         ret, frame = cam.read()
#         if not ret:
#             continue

#         gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#         faces = face_cascade.detectMultiScale(gray, 1.3, 5)

#         if len(faces) == 1:
#             cv2.imwrite(save_path, frame)
#             break

#         elapsed = (cv2.getTickCount() - start_time) / freq
#         if elapsed > timeout:
#             cam.release()
#             cv2.destroyAllWindows()
#             return None

#     cam.release()
#     cv2.destroyAllWindows()
#     return save_path


import os
import cv2
from ultralytics import YOLO
from deepface import DeepFace
from PIL import Image

# 🔧 Helper: Load YOLO model
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


# LOAD MODELS ONCE (IMPORTANT)
yolo_model = _load_yolo_model()
DeepFace.build_model("ArcFace")


# Extract face
def extract_face(image_path: str, face_type: str):
    """
    Extract face from image using YOLO.
    Returns saved face image path or None
    """

    results = yolo_model.predict(image_path)[0]
    image = Image.open(image_path)

    temp_dir = "temp_faces"
    os.makedirs(temp_dir, exist_ok=True)

    if not hasattr(results, "boxes") or len(results.boxes.xyxy) == 0:
        return None

    x1, y1, x2, y2 = map(int, results.boxes.xyxy[0])
    face_img = image.crop((x1, y1, x2, y2))

    face_path = os.path.join(temp_dir, f"{face_type}_face.jpg")
    face_img.save(face_path)

    return face_path


# BACKWARD COMPATIBILITY
def extract_face_from_id_card(id_card_path: str):
    return extract_face(
        image_path=id_card_path,
        face_type="id"
    )


# Compare faces (ArcFace)
def compare_faces(face1_path: str, face2_path: str):

    result = DeepFace.verify(
        img1_path=face1_path,
        img2_path=face2_path,
        model_name="ArcFace",
        enforce_detection=True,
        distance_metric="cosine"
    )

    distance = result["distance"]
    is_match = distance < 0.60

    return is_match, distance


# DUPLICATE FACE CHECK
def check_duplicate_face(new_face_path: str, db, exclude_user_id=None):
    """
    Check if this face already exists in database.
    Same user ko ignore karta hai.
    """

    from app import models  # prevent circular import

    query = db.query(models.User).filter(
        models.User.role == "driver"
    )

    # 👇 SAME USER KO IGNORE KARO
    if exclude_user_id:
        query = query.filter(models.User.id != exclude_user_id)

    existing_drivers = query.all()

    for user in existing_drivers:

        if not user.nic_image_url:
            continue

        try:
            stored_face = extract_face(user.nic_image_url, face_type="stored")

            if not stored_face:
                continue

            is_match, distance = compare_faces(stored_face, new_face_path)

            if is_match:
                print("Duplicate face detected. Distance:", distance)
                return True

        except Exception:
            continue

    return False


# Capture Live Image
def capture_live_image(save_path: str = "uploads/live.jpg", timeout: int = 10):

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
