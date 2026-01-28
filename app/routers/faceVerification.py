import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.face_verification.service import (
    extract_face_from_id_card,
    extract_face,
    compare_faces,
    capture_live_image
)

router = APIRouter(
    prefix="/face-verification",
    tags=["Face Verification"]
)

@router.post("/verify-cnic")
def verify_cnic(
    cnic_image: UploadFile = File(...)
):
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    cnic_path = os.path.join(upload_dir, f"cnic_{cnic_image.filename}")

    # Save CNIC image
    with open(cnic_path, "wb") as f:
        f.write(cnic_image.file.read())

    # 1️⃣ Extract CNIC face
    id_face_path = extract_face_from_id_card(cnic_path)
    if not id_face_path:
        return {"verified": False, "message": "No face detected on CNIC"}

    # 2️⃣ Open camera & capture live image
    live_image_path = capture_live_image()
    if not live_image_path:
        return {"verified": False, "message": "Live face not detected"}

    # 3️⃣ Extract live face
    live_face_path = extract_face(live_image_path, face_type="live")
    if not live_face_path:
        return {"verified": False, "message": "No face detected in live image"}

    # 4️⃣ Compare faces
    is_match, distance = compare_faces(id_face_path, live_face_path)

    # Cleanup
    shutil.rmtree("temp_faces", ignore_errors=True)
    shutil.rmtree(upload_dir, ignore_errors=True)

    if not is_match:
        return {
            "verified": False,
            "message": "Face verification failed",
            "distance": distance
        }

    return {
        "verified": True,
        "message": "Face verified successfully",
        "distance": distance
    }
