import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text
from routes.user import generate_token, login_user
from database.models import UserData, Counters
from schema.distance_models import Location
from utils.global_settings import settings
from auth import *
from schema.user_models import *
from database.db import get_db
from main import app
from pydantic import BaseModel
from datetime import timedelta, datetime

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

# Define the access token functionfrom datetime import timedelta
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
async def test_create_database():
    db= next(get_test_db())
    assert db is not None

@pytest.mark.asyncio
async def test_get_db():
    db= next(get_test_db())
    assert isinstance(db, Session)

@pytest.mark.asyncio
async def test_regitser_user_success(mocker):
    db= next(get_test_db())

    db.execute(_off)
    db.execute(_insert)
    db.commit()

    # mocking functions
    mocker.patch("auth.hash_password", return_value= "hashedpassword123")
    mocker.patch("utils.helpers.get_ETA", return_value= 5)
    # mocker.patch("schema.user_models.GenerateTokenRequest", )

    settings.counters = {
        1:{1:0, 2:0}
    }

    # test data
    request_data = GenerateTokenRequest(
        name="new_user",
        password="password",
        service_id=1,
        location=Location(latitude=27.0, longitude=69.0)
    )
    
    # request simulation
    result = await generate_token(request= request_data, db=db,)

    assert result["success"] == True
    assert "User new_user registered to counter" in result["data"]["message"]

    db.execute(text("DELETE FROM counter WHERE id = 1"))
    db.commit()
    db.execute(_on)
    db.commit()

@pytest.mark.asyncio
async def test_login_user_success(mocker):
    db = next(get_test_db())

    db.execute(_off)
    db.execute(_insert)
    db.commit()

    # test data
    name = "test_user"
    password = "password"
    counter = 1
    pos =  1
    request_data = UserLoginRequest(
        name = name,
        password = password
    )


    # Create a test user
    hashed_password = hash_password(password)
    user_data = UserData(name=name, hashed_password=hashed_password, counter=counter, pos=pos)
    db.add(user_data)
    db.commit()

    # mocking functions
    mocker.patch("auth.verify_password", return_value=True)
    mocker.patch("auth.create_access_token", return_value="access_token")

    # test data
    username = "test_user"
    password = "password"

    # request simulation
    response = await login_user(request = request_data, db=db)
    
    assert len(response) == 3  # Update the assertion to expect 3 values
    assert response["success"] == True
    assert response["error"] == None
    assert len(response["data"]) == 2
    assert response["data"][0]["token_type"] == "bearer"
    assert response["data"][1]["username"] == user_data.name
    assert response["data"][1]["counter number"] == user_data.counter
    assert response["data"][1]["position"] == user_data.pos

    db.execute(text("DELETE FROM counter WHERE id = 1"))
    db.commit()
    db.execute(_on)
    db.commit()

@pytest.mark.asyncio
async def test_login_user_invalid_credentials(mocker):
    db = next(get_test_db())

    db.execute(_off)
    db.execute(_insert)
    db.commit()

    # Create a test user
    user_name = "test_user"
    user_password = "password"
    hashed_password = hash_password(user_password)
    user_data = UserData(name=user_name, hashed_password=hashed_password, counter=1, pos=1)
    db.add(user_data)
    db.commit()

    # mocking functions
    mocker.patch("auth.verify_password", return_value=False)

    # test data
    user_request = UserLoginRequest(
    name = "test_user",
    password = "wrong_password"
    )
    # request simulation
    try:
        await login_user(request= user_request, db=db)
    except HTTPException as e:
        assert e.status_code == 401
        assert e.detail == "Invalid credentials"

    db.execute(text("DELETE FROM counter WHERE id = 1"))
    db.commit()
    db.execute(_on)
    db.commit()

@pytest.mark.asyncio
async def test_login_user_user_not_found(mocker):
    db = next(get_test_db())

    db.execute(_off)
    db.execute(_insert)
    db.commit()

    # test data
    user_request = UserLoginRequest(
        name = "non_existent_user",
        password = "password"
        )

    # check if user exists
    user = db.query(UserData).filter(UserData.name == user_request.name).first()
    assert user is None

    # request simulation
    try:
        await login_user(request=  user_request, db=db)

        assert False, "Expected HTTPException"
    except HTTPException as e:
        assert e.status_code == 404
        assert e.detail == "User not found"

    db.execute(text("DELETE FROM counter WHERE id = 1"))
    db.commit()
    db.execute(_on)
    db.commit()
