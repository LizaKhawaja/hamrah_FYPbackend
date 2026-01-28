from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os, uuid, shutil
import requests  
from .. import models, schemas, utils
from ..database import get_db
from app.face_verification.service import extract_face, compare_faces

router = APIRouter(prefix="/users", tags=["Users"])


# ============================
# 🚶 PASSENGER SIGNUP (JSON)
# ============================
@router.post("/passenger", response_model=schemas.UserOut)
def create_passenger(
    user: schemas.PassengerCreate,
    db: Session = Depends(get_db)
):
    student = db.query(models.DSUStudent).filter_by(
        dsu_reg_id=user.dsu_reg_id
    ).first()

    if not student:
        raise HTTPException(status_code=400, detail="Invalid DSU Registration ID")

    if db.query(models.User).filter(models.User.dsu_reg_id == user.dsu_reg_id).first():
        raise HTTPException(status_code=400, detail="DSU Registration ID already registered")

    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    if db.query(models.User).filter(models.User.phone_number == user.phone_number).first():
        raise HTTPException(status_code=400, detail="Phone number already exists")

    hashed_password = utils.hash_pass(user.password)

    otp_code = utils.generate_otp()
    otp_expiry = datetime.utcnow() + timedelta(minutes=3)

    user_data = user.model_dump(exclude={"password"})

    new_user = models.User(
        **user_data,
        password=hashed_password,
        role="passenger",
        is_verified=False,
        otp_code=otp_code,
        otp_expiry=otp_expiry
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ============================
# 🚗 DRIVER SIGNUP (FORM + FILE)
# ============================

# @router.post("/driver")
# def create_driver(
#     first_name: str = Form(...),
#     last_name: str = Form(...),
#     dsu_reg_id: str = Form(...),
#     phone_number: str = Form(...),
#     email: str = Form(...),
#     password: str = Form(...),
#     license_image_url: str = Form(...),
#     vehicle_number: str = Form(...),
#     mode_of_transport: str = Form(...),

#     cnic_image: UploadFile = File(...),
#     live_image: UploadFile = File(...),

#     db: Session = Depends(get_db)
# ):
#     # ---------------------------
#     # DSU + DUPLICATE CHECKS
#     # ---------------------------
#     student = db.query(models.DSUStudent).filter_by(
#         dsu_reg_id=dsu_reg_id
#     ).first()

#     if not student:
#         raise HTTPException(status_code=400, detail="Invalid DSU Registration ID")

#     if db.query(models.User).filter(models.User.dsu_reg_id == dsu_reg_id).first():
#         raise HTTPException(status_code=400, detail="DSU Registration ID already registered")

#     if db.query(models.User).filter(models.User.email == email).first():
#         raise HTTPException(status_code=400, detail="Email already exists")

#     if db.query(models.User).filter(models.User.phone_number == phone_number).first():
#         raise HTTPException(status_code=400, detail="Phone number already exists")

#     # ---------------------------
#     # SAVE IMAGES
#     # ---------------------------
#     upload_dir = "uploads"
#     os.makedirs(upload_dir, exist_ok=True)

#     cnic_path = os.path.join(
#         upload_dir, f"{first_name.lower()}_cnic_{uuid.uuid4()}.jpg"
#     )
#     live_path = os.path.join(
#         upload_dir, f"{first_name.lower()}_live_{uuid.uuid4()}.jpg"
#     )

#     with open(cnic_path, "wb") as f:
#         f.write(cnic_image.file.read())

#     with open(live_path, "wb") as f:
#         f.write(live_image.file.read())

#     # ---------------------------
#     # FACE VERIFICATION
#     # ---------------------------
#     id_face = extract_face(cnic_path, face_type="id")
#     live_face = extract_face(live_path, face_type="live")

#     if not id_face or not live_face:
#         os.remove(cnic_path)
#         os.remove(live_path)
#         shutil.rmtree("temp_faces", ignore_errors=True)
#         raise HTTPException(status_code=400, detail="Face not detected properly")

#     is_match, distance = compare_faces(id_face, live_face)
#     shutil.rmtree("temp_faces", ignore_errors=True)

#     if not is_match:
#         os.remove(cnic_path)
#         os.remove(live_path)
#         raise HTTPException(
#             status_code=400,
#             detail=f"Face verification failed (distance={distance:.3f})"
#         )

#     # ---------------------------
#     # CREATE DRIVER USER
#     # ---------------------------
#     hashed_password = utils.hash_pass(password)

#     otp_code = utils.generate_otp()
#     otp_expiry = datetime.utcnow() + timedelta(minutes=3)

#     new_user = models.User(
#         first_name=first_name,
#         last_name=last_name,
#         dsu_reg_id=dsu_reg_id,
#         phone_number=phone_number,
#         email=email,
#         password=hashed_password,
#         nic_image_url=cnic_path,
#         live_image_url=live_path,
#         license_image_url=license_image_url,
#         role="driver",
#         is_verified=False,
#         otp_code=otp_code,
#         otp_expiry=otp_expiry
#     )

#     db.add(new_user)
#     db.commit()
#     db.refresh(new_user)

#     # ---------------------------
#     # VEHICLE
#     # ---------------------------
#     if db.query(models.Vehicle).filter(
#         models.Vehicle.vehicle_number == vehicle_number
#     ).first():
#         raise HTTPException(status_code=400, detail="Vehicle already registered")

#     vehicle = models.Vehicle(
#         user_id=new_user.id,
#         vehicle_number=vehicle_number,
#         mode_of_transport=mode_of_transport
#     )

#     db.add(vehicle)
#     db.commit()

#     return {
#         "message": "Driver registered successfully. OTP sent to email.",
#         "distance": distance
#     }

def download_image(url: str, save_path: str):
    # Accept Firebase Storage or any valid http/https URL
    # if "firebasestorage.googleapis.com" not in url:
    #     raise HTTPException(status_code=400, detail="Invalid image source")
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid image source - must be a valid URL")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Unable to download image")
        with open(save_path, "wb") as f:
            f.write(response.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error downloading image: {str(e)}")

@router.post("/driver")
def create_driver(
    first_name: str = Form(...),
    last_name: str = Form(...),
    dsu_reg_id: str = Form(...),
    phone_number: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    gender: str = Form(...),
    license_image_url: str = Form(...),
    vehicle_number: str = Form(...),
    mode_of_transport: str = Form(...),

    cnic_image_url: str = Form(...),
    live_image_url: str = Form(...),

    db: Session = Depends(get_db)
):
    # ---------------------------
    # DSU + DUPLICATE CHECKS
    # ---------------------------
    student = db.query(models.DSUStudent).filter_by(
        dsu_reg_id=dsu_reg_id
    ).first()

    if not student:
        raise HTTPException(status_code=400, detail="Invalid DSU Registration ID")

    if db.query(models.User).filter(models.User.dsu_reg_id == dsu_reg_id).first():
        raise HTTPException(status_code=400, detail="DSU Registration ID already registered")

    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    if db.query(models.User).filter(models.User.phone_number == phone_number).first():
        raise HTTPException(status_code=400, detail="Phone number already exists")

    # ---------------------------
    # SAVE IMAGES
    # ---------------------------
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    cnic_path = os.path.join(upload_dir, f"{first_name.lower()}_cnic_{uuid.uuid4()}.jpg")
    live_path = os.path.join(upload_dir, f"{first_name.lower()}_live_{uuid.uuid4()}.jpg")

    download_image(cnic_image_url, cnic_path)
    download_image(live_image_url, live_path)

    # ---------------------------
    # FACE VERIFICATION
    # ---------------------------
    id_face = extract_face(cnic_path, face_type="id")
    live_face = extract_face(live_path, face_type="live")

    if not id_face or not live_face:
        os.remove(cnic_path)
        os.remove(live_path)
        shutil.rmtree("temp_faces", ignore_errors=True)
        raise HTTPException(status_code=400, detail="Face not detected properly")

    is_match, distance = compare_faces(id_face, live_face)
    shutil.rmtree("temp_faces", ignore_errors=True)

    if not is_match:
        os.remove(cnic_path)
        os.remove(live_path)
        raise HTTPException(
            status_code=400,
            detail=f"Face verification failed (distance={distance:.3f})"
        )

    # ---------------------------
    # CREATE DRIVER USER
    # ---------------------------
    hashed_password = utils.hash_pass(password)

    otp_code = utils.generate_otp()
    otp_expiry = datetime.utcnow() + timedelta(minutes=3)

    new_user = models.User(
        first_name=first_name,
        last_name=last_name,
        dsu_reg_id=dsu_reg_id,
        phone_number=phone_number,
        email=email,
        password=hashed_password,
        gender=gender,
        nic_image_url=cnic_path,
        live_image_url=live_path,
        license_image_url=license_image_url,
        role="driver",
        is_verified=False,
        otp_code=otp_code,
        otp_expiry=otp_expiry
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # ---------------------------
    # VEHICLE
    # ---------------------------
    if db.query(models.Vehicle).filter(
        models.Vehicle.vehicle_number == vehicle_number
    ).first():
        raise HTTPException(status_code=400, detail="Vehicle already registered")

    vehicle = models.Vehicle(
        user_id=new_user.id,
        vehicle_number=vehicle_number,
        mode_of_transport=mode_of_transport
    )

    db.add(vehicle)
    db.commit()

    return {
        "message": "Driver registered successfully. OTP sent to email.",
        "distance": distance
    }



# ============================
# 🔐 VERIFY OTP
# ============================
@router.post("/verify-otp")
def verify_otp(
    data: schemas.OTPVerify,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(
        models.User.email == data.email
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="User already verified")

    if user.otp_code != data.otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if user.otp_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")

    user.is_verified = True
    user.otp_code = None
    user.otp_expiry = None

    db.commit()

    return {"message": "Account verified successfully"}


# ============================
# 🔁 RESEND OTP
# ============================
@router.post("/resend-otp")
def resend_otp(
    data: schemas.ResendOTP,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(
        models.User.email == data.email
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="User already verified")

    user.otp_code = utils.generate_otp()
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=3)

    db.commit()

    return {"message": "New OTP sent successfully"}
