from fastapi import FastAPI
from .database import engine
from . import models
from .routers import auth, user, faceVerification, rides, ride_request

# Ye line ensure karo ke models imported ho chuke hain
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(faceVerification.router)
app.include_router(rides.router)
app.include_router(ride_request.router)



