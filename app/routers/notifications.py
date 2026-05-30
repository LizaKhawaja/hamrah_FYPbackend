from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import DeviceToken
from app.schemas import TokenRequest
from app.services.fcm_service import send_notification
from app import oauth2

router = APIRouter()


# Save token
@router.post("/save-token")
def save_token(
    data: TokenRequest,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    # duplicate check (same token dubara save na ho)
    existing = db.query(DeviceToken).filter(
        DeviceToken.user_id == current_user.id,
        DeviceToken.token == data.token
    ).first()

    if not existing:
        db.add(DeviceToken(user_id=current_user.id, token=data.token))
        db.commit()

    return {"message": "Token saved successfully"}


# Test notification
@router.post("/test-notify")
def test_notify(
    user_id: int,
    db: Session = Depends(get_db)
):
    tokens = db.query(DeviceToken).filter(DeviceToken.user_id == user_id).all()
    token_list = [t.token for t in tokens]

    send_notification(token_list, "Test ", "Hello from backend")

    return {"message": "Notification sent"}