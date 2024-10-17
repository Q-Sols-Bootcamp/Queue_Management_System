import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy import text
from database.models import UserData#, Counter
from schema.distance_models import Location
from auth import hash_password, SECRET_KEY, ALGORITHM
from database.db import get_db
from main import app
from pydantic import BaseModel
from datetime import timedelta, datetime
from routes.get_distance import update_eta
from schema.distance_models import UpdateEtaReaquest
from jose import jwt#, JWTError

_off = text("SET FOREIGN_KEY_CHECKS = 0;")
_on = text("SET FOREIGN_KEY_CHECKS = 1;")
_insert = text("INSERT INTO counter (id, service_id, in_queue, total_tat) VALUES (1, 1, 0, 0);")

client = TestClient(app)
@pytest.fixture
def client():
    return TestClient(app)

# Mock database dependency
def get_test_db():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

# Define the user model
class User(BaseModel):
    name: str
    hashed_password: str

# Define the access token function
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now() + expires_delta
    else:
        expire = datetime.datetime.now()+ timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@pytest.mark.asyncio
async def test_update_eta_success(mocker):
    db = next(get_test_db())

    db.execute(_off)
    db.execute(_insert)
    db.commit()

    # Create a test user
    name = "test_user"
    password = "password"
    hashed_password = hash_password(password)
    user_data = UserData(name=name, hashed_password=hashed_password, counter=1, pos=1, ETA=10)
    db.add(user_data)
    db.commit()

    # mocking functions
    mocker.patch("utils.helpers.get_ETA", return_value=5)

    # test data
    user_request = UpdateEtaReaquest(
        location = Location(latitude=27.0, longitude=69.0),
        userid = user_data.id,
    )
    

    # request simulation
    result = await update_eta(request = user_request, db=db)

    assert result["success"] == True
    assert "ETA updated successfully" in result["data"]["message"]

    db.execute(text("DELETE FROM counter WHERE id = 1"))
    db.commit()
    db.execute(_on)
    db.commit()

@pytest.mark.asyncio
async def test_update_eta_user_not_found(mocker):
    db = next(get_test_db())

    db.execute(_off)
    db.execute(_insert)
    db.commit()

    # test data
    user_request = UpdateEtaReaquest(
        userid= 21,
        location = Location(latitude= 21, longitude=22)
        )

    # check if user exists
    user = db.query(UserData).filter(UserData.id == user_request.userid).first()
    assert user is None

    # request simulation
    try:
        await update_eta(request = user_request, db=db)
        assert False, "Expected HTTPException"
    except HTTPException as e:
        assert e.status_code == 404
        assert e.detail == "Failed to Update ETA"

    db.execute(text("DELETE FROM counter WHERE id = 1"))
    db.commit()
    db.execute(_on)
    db.commit()
    
