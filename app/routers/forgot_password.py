from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets

from .. import models, utils, schemas
from ..database import get_db
from ..services import mail_service

router = APIRouter(prefix="/password", tags=["Forgot Password"])

#  REQUEST PASSWORD RESET
@router.post("/forgot")
def forgot_password(
    request: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Request password reset link via email
    """
    user = db.query(models.User).filter(
        models.User.email == request.email
    ).first()

    if not user:
        # Don't reveal if email exists or not for security
        return {"message": "If the email exists, a password reset link has been sent"}

    # 🔐 Generate secure reset token
    reset_token = secrets.token_urlsafe(32)
    expiry_time = datetime.utcnow() + timedelta(minutes=15)

    user.reset_token = reset_token
    user.reset_token_expiry = expiry_time

    db.commit()

    # 🔗 Reset link (frontend will handle this)
    # Update this URL to match your frontend reset password page
    reset_link = f"http://localhost:3000/reset-password?token={reset_token}"

    # 📧 Send email with reset link
    try:
        mail_service.send_reset_email(user.email, reset_link)
    except Exception as e:
        # Rollback token if email fails
        user.reset_token = None
        user.reset_token_expiry = None
        db.commit()
        raise HTTPException(
            status_code=500,
            detail="Failed to send email. Please try again later."
        )

    return {"message": "Password reset link sent to email"}


#  VERIFY RESET TOKEN
@router.get("/verify-token/{token}")
def verify_reset_token(token: str, db: Session = Depends(get_db)):
    """
    Verify if reset token is valid (called when user clicks email link)
    """
    user = db.query(models.User).filter(
        models.User.reset_token == token
    ).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    if user.reset_token_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")

    return {"message": "Token is valid", "email": user.email}



#  RESET PASSWORD
@router.post("/reset")
def reset_password(
    request: schemas.ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password using the token from email link
    """
    user = db.query(models.User).filter(
        models.User.reset_token == request.token
    ).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if user.reset_token_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")

    # 🔐 Hash new password
    hashed_password = utils.hash_pass(request.new_password)

    user.password = hashed_password
    user.reset_token = None
    user.reset_token_expiry = None

    db.commit()

    return {"message": "Password reset successfully"}


