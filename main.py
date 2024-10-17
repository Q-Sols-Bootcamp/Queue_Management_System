from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer
from database.db import SessionLocal
from contextlib import asynccontextmanager
from utils.helpers import clear_queue
from routes.counter_operator import router as operator_router
from routes.user import router as user_router
from routes.services_crud import router as services_crud_router
from routes.get_distance import router as distance_router
from auth import verify_access_token
import os, logging
from utils.global_settings import setup_logging
from dotenv import load_dotenv

setup_logging()
logger = logging.getLogger(__name__)

load_dotenv()

env_variables = ['DISTANCEMATRIX_API_KEY', 'SECRET_KEY', 'ALGORITHM', 'DATABASE_URL']
logging.info(f"{env_variables}")
def check_env():
    """
    Validate environment variables.

    This function checks if the required environment variables are set.
    If any variable is empty or not set, it prints an error message and exits the program.

    Args:
        None

    Returns:
        None
    """
    for var in env_variables:
        if not os.getenv(var):
            logging.debug(f"{var} is empty or not set")
            exit(1)
        else:
            logging.debug(f"Environment variable validation completed: {var}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    check_env()
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
    """
    Get the current user from the access token.

    This function verifies the access token and returns the username of the current user.

    Args:
        token (str): The access token to verify.

    Returns:
        str: The username of the current user.
    """
    username = verify_access_token(token)
    return username

# Creating instance of the FastAPI app
description = """
* An auto queuing system that dynamically rebalances the users, based on their ETA
"""
app = FastAPI(lifespan=lifespan,
    title="Queue Management System",
    description=description,
    # summary="",
    version="0.0.1",
    # terms_of_service="http://example.com/terms/",
    # contact={
    #     "name": ,
    #     "url": ,
    #     "email": ,
    # },
    # license_info={
    #     "name": ,
    #     "url": ,
    # },
)
app.include_router(services_crud_router)
app.include_router(user_router)
app.include_router(operator_router)
app.include_router(distance_router)
