from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer
from database.db import SessionLocal
from contextlib import asynccontextmanager
from utils.helpers import clear_queue
from routes.counter_operator import router as operator_router
from routes.user import router as user_router
from routes.services_crud import router as services_crud_router
from routes.get_distance import router as distance_router
from utils.global_settings import *
from auth import *

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        clear_queue(db)
    finally:
        # Close the database session after setup
        db.close()
    yield

oauth2_scheme= OAuth2PasswordBearer(tokenUrl= "login")

# dependency to get current user
async def get_current_user(token: str = Depends(oauth2_scheme)):
    username = verify_access_token(token)
    return username

# Creating instance of the FastAPI app
app = FastAPI(lifespan=lifespan)
app.include_router(services_crud_router)
app.include_router(user_router)
app.include_router(operator_router)
app.include_router(distance_router)
