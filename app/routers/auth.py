# from fastapi import APIRouter, Depends, status, HTTPException
# from fastapi.security import OAuth2PasswordRequestForm
# from sqlalchemy.orm import Session
# from .. import database, schemas, models, utils, oauth2

# router = APIRouter(tags=["Authentication"])

# @router.post("/login", response_model=schemas.Token)
# def login(
#     user_credentials: OAuth2PasswordRequestForm = Depends(),
#     db: Session = Depends(database.get_db)
# ):
#     user = db.query(models.User).filter(models.User.dsu_reg_id == user_credentials.username).first()

#     if not user:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

#     if not utils.verify(user_credentials.password, user.password):
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

#     access_token = oauth2.create_access_token(data={"user_id": user.id})
#     return {"access_token": access_token, "token_type": "bearer"}

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import database, schemas, models, utils, oauth2

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=schemas.Token)
def login( user_credentials: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(database.get_db)):
    # 1️⃣ Get user by DSU Registration ID
    user = db.query(models.User).filter( models.User.dsu_reg_id == user_credentials.username).first()

    # 2️⃣ Check if user exists
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # 3️⃣ Check password
    if not utils.verify(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid credentials")

    # 4️⃣ IMPORTANT: Check email/OTP verification
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Please verify your email first")

    # 5️⃣ Create access token
    access_token = oauth2.create_access_token(data={"user_id": user.id})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }