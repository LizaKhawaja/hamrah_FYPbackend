from fastapi import FastAPI
from .database import engine
from . import models
from .routers import auth, user, faceVerification, rides, ride_request, forgot_password

# Ye line ensure karegi ke models import ho chuke hain
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth.router)
app.include_router(forgot_password.router)
app.include_router(user.router)
app.include_router(faceVerification.router)
app.include_router(rides.router)
app.include_router(ride_request.router)



# uvicorn app.main:app --host 0.0.0.0 --port 8000