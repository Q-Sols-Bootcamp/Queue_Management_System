import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from routes.services_crud import add_service, update_service, delete_service
from schema.services_models import CreateServiceRequest, UpdateServiceRequest
from fastapi import HTTPException
from database.db import get_db
from main import app

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

    # Disable foreign key checks and clear the counter and services tables
    db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
    db.execute(text("DELETE FROM counter"))
    db.execute(text("DELETE FROM services"))
    db.commit()

    yield db

    # Clean up
    db.execute(text("DELETE FROM counter"))
    db.execute(text("DELETE FROM services"))
    db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    db.commit()

@pytest.mark.asyncio
async def test_add_service_success(mocker, setup_db):
    db = setup_db

    # Mocking functions
    mocker.patch("database.models.Counter", autospec=True)
    mocker.patch("database.models.Service", autospec=True)

    # Test data
    request = CreateServiceRequest(name="test_service", no_of_counters=1)

    # Request simulation
    response = await add_service(request, db)

    assert response['success'] == True
    assert response['error'] is None
    assert 'data' in response
    assert 'service_id' in response['data']

@pytest.mark.asyncio
async def test_add_service_invalid_request(mocker, setup_db):
    db = setup_db
    
    # Mocking functions
    mocker.patch("database.models.Counter", autospec=True)
    mocker.patch("database.models.Service", autospec=True)

    
    # Test data
    request = CreateServiceRequest(name="test_name", no_of_counters="1")
    
    # request simulation
    try:
        await add_service(request, db)
        assert "Expected HTTPException"
    except HTTPException as e:
        assert e.status_code == 500

@pytest.mark.asyncio
async def test_update_service_success(mocker, setup_db):
    db = setup_db

    # Mocking functions
    mocker.patch("database.models.Counter", autospec=True)
    mocker.patch("database.models.Service", autospec=True)

    # Add initial service
    initial_request = CreateServiceRequest(name="initial_service", no_of_counters=1)
    initial_response = await add_service(initial_request, db)
    service_id = initial_response['data']['service_id']

    # Test data for updating service
    update_request = UpdateServiceRequest(service_id=service_id, name="updated_service", no_of_counters=2)

    # Request simulation
    response = await update_service(update_request, db)

    assert response['success'] == True
    assert response['error'] is None
    assert 'data' in response
    assert response['data']['message'] == 'Service updated successfully'

@pytest.mark.asyncio
async def test_update_service_not_found(mocker, setup_db):
    db = setup_db

    # Mocking functions
    mocker.patch("database.models.Counter", autospec=True)
    mocker.patch("database.models.Service", autospec=True)

    # Test data for updating a non-existent service
    update_request = UpdateServiceRequest(service_id=999, name="non_existent_service", no_of_counters=2)

    # Request simulation
    try:
        await update_service(update_request, db)
        assert False, "Expected HTTPException"
    except HTTPException as e:
        assert e.status_code == 500 

@pytest.mark.asyncio
async def test_update_service_invalid_request(mocker, setup_db):
    db = setup_db

    # Mocking functions
    mocker.patch("database.models.Counter", autospec=True)
    mocker.patch("database.models.Service", autospec=True)

    # Add initial service
    initial_request = CreateServiceRequest(name="initial_service", no_of_counters=1)
    initial_response = await add_service(initial_request, db)
    service_id = int(initial_response['data']['service_id'])

    # Test data for updating service with invalid data
    update_request = UpdateServiceRequest(service_id=service_id, name="updated_service", no_of_counters=-1)

    # Request simulation
    try:
        await update_service(update_request, db)
        assert False, "Expected HTTPException"
    except HTTPException as e:
        assert e.status_code == 500  
        # or the expected status code for validation errors

@pytest.mark.asyncio
async def test_delete_service_success(mocker, setup_db):
    db = setup_db

    # Mocking functions
    mocker.patch("database.models.Counter", autospec=True)
    mocker.patch("database.models.Service", autospec=True)

    # Add initial service
    initial_request = CreateServiceRequest(name="test_service", no_of_counters=1)
    initial_response = await add_service(initial_request, db)
    service_id = initial_response['data']['service_id']

    # Request simulation for deletion
    response = await delete_service(service_id, db)

    assert response['success'] == True
    assert response['error'] is None
    assert 'data' in response
    assert response['data']['message'] == 'Service deleted successfully'

@pytest.mark.asyncio
async def test_delete_service_not_found(mocker, setup_db):
    db = setup_db

    # Mocking functions
    mocker.patch("database.models.Counter", autospec=True)
    mocker.patch("database.models.Service", autospec=True)

    # Test data for deleting a non-existent service
    non_existent_service_id = 999

    # Request simulation
    try:
        await delete_service(non_existent_service_id, db)
        assert False, "Expected HTTPException"
    except HTTPException as e:
        assert e.status_code == 404  # Not Found
        
        
@pytest.mark.asyncio
async def test_delete_service_with_active_users(mocker, setup_db):
    db = setup_db

    # Mocking functions
    mocker.patch("database.models.Counter", autospec=True)
    mocker.patch("database.models.Service", autospec=True)
    mocker.patch("database.models.UserData", autospec=True)

    # Add initial service
    initial_request = CreateServiceRequest(name="test_service", no_of_counters=1)
    initial_response = await add_service(initial_request, db)
    service_id = initial_response['data']['service_id']

    # Mock the query chain for UserData to simulate active users
    mock_query = mocker.patch.object(db, 'query')
    mock_filter = mock_query.return_value.filter
    mock_filter.return_value.count.return_value = 1

    # Request simulation
    try:
        await delete_service(service_id, db)
        assert False, "Expected HTTPException"
    except HTTPException as e:
        assert e.status_code == 400  # Bad Request
        assert 'Service has active users in its queues.' in e.detail
