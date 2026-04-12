from fastapi import FastAPI
from .database import engine
from . import models
from .routers import auth, user, faceVerification, rides, ride_request, forgot_password, notifications
import firebase_admin
from firebase_admin import credentials

# Ye line ensure karegi ke models import ho chuke hain
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth.router)
app.include_router(forgot_password.router)
app.include_router(user.router)
app.include_router(faceVerification.router)
app.include_router(rides.router)
app.include_router(ride_request.router)
app.include_router(notifications.router)


#Firebase INIT 
cred = credentials.Certificate("D:\hamrah\hamrah-notification-2a315-firebase-adminsdk-fbsvc-0f04c3f2ea.json")
firebase_admin.initialize_app(cred)

# uvicorn app.main:app --host 0.0.0.0 --port 8000