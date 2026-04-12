from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DeviceToken
from app.schemas import TokenRequest

router = APIRouter()


# SAVE TOKEN
@router.post("/save-token")
def save_token(data: TokenRequest, db: Session = Depends(get_db)):
    new_token = DeviceToken(
        user_id=data.user_id,
        token=data.token
    )

    db.add(new_token)
    db.commit()

    return {"message": "saved"}


# TEST NOTIFICATION
@router.post("/test-notify")
def test_notify(user_id: int, db: Session = Depends(get_db)):

    tokens = db.query(DeviceToken).filter(DeviceToken.user_id == user_id).all()
    token_list = [t.token for t in tokens]

    from app.services.fcm_service import send_notification

    send_notification(token_list, "Test 🚀", "Hello from backend")

    return {"message": "sent"}