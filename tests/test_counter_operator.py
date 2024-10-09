import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text
from routes.counter_operator import *
from database.models import Services
from auth import *
from database.db import get_db
from main import app
from fastapi import HTTPException
import utils.helpers, utils.global_settings
from schema.operator_models import *

client = TestClient(app)

# Mock database dependency
def get_test_db():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def setup_db():
    db = next(get_test_db())

    # Disable foreign key checks and clear the services table
    db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
    db.execute(text("DELETE FROM services"))
    db.commit()

    yield db

    # Clean up
    db.execute(text("DELETE FROM services"))
    db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    db.commit()

@pytest.mark.asyncio
async def test_select_services_success(mocker, setup_db):
    db = setup_db

    # Mocking functions
    mocker.patch("database.models.Services", autospec=True)

    # Add initial services
    service1 = Services(id=1, name="service1", no_of_counters=1)
    service2 = Services(id=2, name="service2", no_of_counters=2)
    db.add(service1)
    db.add(service2)
    db.commit()

    # Request simulation
    response = await select_services(db)

    assert response['success'] == True
    assert response['error'] is None
    assert 'data' in response
    assert len(response['data']) == 2
    assert response['data'][0].name == "service1"
    assert response['data'][1].name == "service2"

@pytest.mark.asyncio
async def test_select_services_no_services(mocker, setup_db):
    db = setup_db

    # Mocking functions
    mocker.patch("database.models.Services", autospec=True)

    # Request simulation
    response = await select_services(db)

    assert response['success'] == True
    assert response['error'] is None
    assert 'data' in response
    assert len(response['data']) == 0

@pytest.mark.asyncio
async def test_select_services_db_error(mocker, setup_db):
    db = setup_db

    # Mocking functions
    mocker.patch("database.models.Services", autospec=True)
    
    # Mock the database query to raise an exception
    mocker.patch.object(db, 'query', side_effect=Exception("Database error"))

    # Request simulation
    try:
        await select_services(db)
        assert False, "Expected HTTPException"
    except HTTPException as e:
        assert e.status_code == 500
        assert 'Database error' in e.detail['error']['message']

@pytest.mark.asyncio
async def test_select_counter_success(mocker, setup_db):
    db = setup_db

    # Import the settings object from the utils.global_settings module
    from utils.global_settings import settings

    # Mocking functions
    mocker.patch.object(settings, 'counters', {1: {1: 10, 2: 20}, 2: {1: 30, 2: 40}})

    # Print out the mocked settings.counters value
    print("Mocked settings.counters:", settings.counters)

    # Request simulation
    response = await select_counter(service_id=1)

    # Print out the response
    print(f"Response: {response}")

    assert response['success'] == True
    assert response['error'] is None
    assert 'data' in response
    assert response['data'] ==  {'counters': {1: 10, 2: 20}}

@pytest.mark.asyncio
async def test_select_counter_service_not_found(mocker, setup_db):
    db = setup_db

    # Mocking functions
    mocker.patch("utils.global_settings.settings", autospec=True)
    settings = utils.global_settings.settings
    settings.counters = {1: {1: 10, 2: 20}, 2: {1: 30, 2: 40}}

    # Request simulation
    try:
        await select_counter(service_id=3)
        assert False, "Expected HTTPException"
    except HTTPException as e:
        assert e.status_code == 500
        assert 'counters for the selected service' in e.detail


@pytest.mark.asyncio
async def test_get_queue_success(mocker, setup_db):
    db = setup_db

    # Create a test user data
    name = 'test_user'
    password= 'password'
    hashed_password= hash_password(password)
    test_counter = 1
    test_service = 1
    
    user_request = SelectQueue(
        counter=test_counter,
        service_id=test_service, 
    )
    
    service = Services(id= 1, name= 'test', no_of_counters= 2)
    user_data = UserData(name=name, hashed_password=hashed_password, service_id=test_service, counter=test_counter, pos=1)
    db.add(service)
    db.add(user_data)
    db.commit()

    # Mocking functions
    mocker.patch("utils.global_settings.settings", autospec=True)
    settings = utils.global_settings.settings
    settings.counters = {1: {1: 10, 2: 20}, 2: {1: 30, 2: 40}}

    # Request simulation
    response = await get_queue(request=user_request, db=db)

    # Print out the response
    print(f"Response: {response}")

    assert response['success'] == True
    assert response['error'] is None
    assert 'data' in response
    assert len(response['data']) == 1
    assert response['data'][0].service_id == 1
    assert response['data'][0].counter == 1
    assert response['data'][0].pos == 1

@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_queue_empty(mocker, setup_db):
    db = setup_db

    # Mocking database query to simulate no service found scenario
    mock_query = mocker.patch.object(db, 'query')

    # Mock the service query chain
    mock_service_filter = mock_query.return_value.filter
    mock_service_filter.return_value.first.return_value = Services(id=1, name="Test Service")

    # Mock the queue (UserData) query chain
    mock_user_filter = mock_service_filter.return_value.filter
    mock_user_filter.return_value.order_by.return_value.all.return_value = []  # Simulate empty queue

    # Test data for the request
    user_request = SelectQueue(
        service_id=1,
        counter=1
    )
# Mocking functions
    mocker.patch("utils.global_settings.settings", autospec=True)
    settings = utils.global_settings.settings
    settings.counters = {1: {1: 0, 2: 20}, 2: {1: 30, 2: 40}}

    user_request= SelectQueue(
        service_id= 1,
        counter= 1
    )

    # Request simulation
    response = await get_queue(request = user_request, db=db)

    # Print out the response
    print(f"Response: {response}")

    assert response['success'] == True
    assert response['error'] is None
    assert 'data' in response
    # assert response['data'] == ["queue is empty"]

@pytest.mark.asyncio
async def test_get_queue_service_id_not_found(mocker, setup_db):
    db = setup_db

# Create a test user data
    name = 'test_user'
    password= 'password'
    hashed_password= hash_password(password)
    user_data = UserData(name=name, hashed_password=hashed_password, service_id=1, counter=1, pos=1)
    db.add(user_data)
    db.commit()

    # Mocking functions
    mocker.patch("utils.global_settings.settings", autospec=True)
    settings = utils.global_settings.settings
    settings.counters = {1: {1: 10, 2: 20}, 2: {1: 30, 2: 40}}

    user_request= SelectQueue(
        service_id= 1,
        counter= 1
    )

    # Request simulation
    try:
        await get_queue(request = user_request, db=db)
        assert False, "Expected HTTPException"
    except HTTPException as e:
        assert e.status_code == 500
        assert 'Internal Error' in e.detail

@pytest.mark.asyncio
async def test_pop_next_user_success(mocker, setup_db):
    db = setup_db
    
    # Create test user data
    name1, name2 = 'test_user1', 'test_user2' 
    password1, password2= 'password1', 'password2'
    hashed_password1, hashed_password2= hash_password(password1), hash_password(password2)
    user_data1 = UserData(name=name1, hashed_password=hashed_password1, service_id=1, counter=1, pos=1)
    # user_data1 = UserData(service_id=1, counter=1, pos=1)
    user_data2 = UserData(name=name2, hashed_password=hashed_password2, service_id=1, counter=1, pos=2)
    db.add(user_data1)
    db.add(user_data2)
    db.commit()

    user_request = SelectQueue(
        service_id=1,
        counter=1
    )

    # Mocking functions
    mocker.patch("utils.global_settings.settings", autospec=True)
    settings = utils.global_settings.settings
    settings.counters = {1: {1: 10, 2: 20}, 2: {1: 30, 2: 40}}

    try:
        await pop_next_user(request= user_request, db=db)
        # assert False, "Expected HTTPException"
    except HTTPException as e:
        assert e.status_code == 404
        assert e.detail == "Not found"

@pytest.mark.asyncio
async def test_pop_next_user_empty(mocker, setup_db):
    db = setup_db

    # Mocking functions
    mocker.patch("utils.global_settings.settings", autospec=True)
    settings = utils.global_settings.settings
    settings.counters = {1: {1: 0, 2: 20}, 2: {1: 30, 2: 40}}

    user_request = SelectQueue(
        service_id=1,
        counter=1
    )

    # Request simulation

    try:
        response = await pop_next_user(request= user_request, db=db)
    except HTTPException as e:
        assert e.status_code == 404
        assert e.detail == 'Not found'
