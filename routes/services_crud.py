from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from database.models import UserData, Service, Counter
from database.db import get_db
from schema.services_models import CreateServiceRequest, UpdateServiceRequest, ServiceResponse
import logging
from utils.global_settings import settings, setup_logging
from status import StatusCode, StatusResponse
from sqlalchemy.exc import SQLAlchemyError

setup_logging()
logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/services",
    tags=["services"]
)

@router.post("", response_model=StatusResponse)
async def add_service(request: CreateServiceRequest, db: Session = Depends(get_db)):
    """
    Create a new service.

    This endpoint creates a new service with the specified name and number of counters.

    Args:
        request (CreateServiceRequest): A request object containing the service name and number of counters.
        db (Session, optional): A database session. Defaults to Depends(get_db).

    Returns:
        StatusResponse: A response object indicating the status of the service creation.

    Raises:
        HTTPException: If a service with the same name already exists (409).
    """
    already_exists= (
        db.query(Service)
        .filter(Service.name == request.name)
        .first()
    )
    if not already_exists:
    
        # Create a new service in the database
        new_service = Service(name=request.name, no_of_counters=request.no_of_counters)
        db.add(new_service)
        db.flush()  # Commit to assign an ID to new_service

        # for i in range(request.no_of_counters):
        #     new_counter = Counters(no_of_counters=request.no_of_counters)

        # Re-query the database to fetch the newly created service (to ensure service ID is available)
        db.refresh(new_service)

        # Initialize counters for the new service
        service_counters = {}
        new_counters=[]

        # Use global_counter to assign unique counter numbers across all services

        try:
            for _ in range(request.no_of_counters):
                service_counters[settings.global_counter] = 0  # No users in the counter at start
                logging.info(f"Assigned counter {settings.global_counter} to service {new_service.name}")
                new_counter = Counter(id=settings.global_counter, service_id = new_service.id)
                new_counters.append(new_counter)
            
                settings.global_counter += 1  # Increment global counter for the next assignment
            db.add_all(new_counters)
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            logging.error(f"Error occurred while assigning counters: {str(e)}")
            raise HTTPException(status_code=StatusCode.INTERNAL_SERVER_ERROR.value, detail=StatusCode.INTERNAL_SERVER_ERROR.message)
        # db.refresh(new_counters)

        # Add this service's counters to the global counters dictionary using the service ID
        settings.counters[new_service.id] = service_counters

        # Log the initialization
        logging.info(f"Initialized counters for service {new_service.name}: {service_counters}")
        logging.info(f"Global counters state after addition: {settings.counters}")

        service_to_return = ServiceResponse(id=new_service.id, name=new_service.name, no_of_counters=new_service.no_of_counters)

        return StatusResponse(status_code=StatusCode.CREATED.value, status_message=StatusCode.CREATED.message, data=service_to_return)
        

    else:
        db.rollback()
        raise HTTPException(status_code=StatusCode.CONFLICT.value, detail=StatusCode.CONFLICT.message)




# Update service details (name and/or no_of_counters)
@router.put("", response_model=StatusResponse)
async def update_service(request: UpdateServiceRequest, db: Session = Depends(get_db)):
    """
    Update service details.

    This endpoint updates the name and/or number of counters for an existing service.

    Args:
        request (UpdateServiceRequest): A request object containing the service ID, 
                                        new name (optional), and new number of counters (optional).
        db (Session, optional): A database session. Defaults to Depends(get_db).

    Returns:
        StatusResponse: A response object containing the updated service details.

    Raises:
        HTTPException: 
            - If the service is not found (404).
            - If there are active users in the service queues (400).
            - If there's an error updating the service (500).
    """    
    service = db.query(Service).filter(Service.id == request.service_id).first()
    if not service:
        raise HTTPException(status_code=StatusCode.NOT_FOUND.value, detail=StatusCode.NOT_FOUND.message)

    # Check for active users in the service queues
    if db.query(UserData).filter(UserData.service_id == request.service_id).count() > 0:
        raise HTTPException(status_code=StatusCode.BAD_REQUEST.value, detail=StatusCode.BAD_REQUEST.message)

    # Update service name if provided
    if request.name:
        service.name = request.name

    # Update number of counters if provided
    if request.no_of_counters is not None:
        current_counters = len(settings.counters.get(service.id, {}))
        if request.no_of_counters > current_counters:
            for _ in range(current_counters + 1, request.no_of_counters + 1):
                new_counter = Counter(id=settings.global_counter, service_id=service.id)
                db.add(new_counter)
                settings.counters[service.id][settings.global_counter] = 0  # Initialize new counter
                settings.global_counter += 1
        else:
            for i in range(current_counters, request.no_of_counters, -1):
                if settings.counters[service.id][i] > 0:
                    raise HTTPException(status_code=StatusCode.BAD_REQUEST.value, detail=StatusCode.BAD_REQUEST.message)
                del settings.counters[service.id][i]
                db.query(Counter).filter(Counter.id == i).delete()

        service.no_of_counters = request.no_of_counters

    # Commit changes to the database
    try:
        db.commit()
        db.refresh(service)
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Update_service failed because: {str(e)}")
        raise HTTPException(status_code=StatusCode.INTERNAL_SERVER_ERROR.value, detail=StatusCode.INTERNAL_SERVER_ERROR.message)

    service_to_return = ServiceResponse(id=service.id, name=service.name, no_of_counters=service.no_of_counters)
    return StatusResponse(status_code=StatusCode.OK.value, status_message=StatusCode.OK.message, data=service_to_return)

    
# Delete a service
@router.delete("/{service_id}", response_model=StatusResponse)
async def delete_service(service_id: int, db: Session = Depends(get_db)):
    """
    Delete a service.

    This endpoint removes a service and its associated counters from the system.

    Args:
        service_id (int): The ID of the service to be deleted.
        db (Session, optional): A database session. Defaults to Depends(get_db).

    Returns:
        StatusResponse: A response object indicating the status of the service deletion
        and the info of the deleted service.

    Raises:
        HTTPException:
            - If the service is not found (404).
            - If there are active users in the service queues (400).
            - If there's an error during the deletion process (500).
    """
    service = db.query(Service).filter(Service.id == service_id).first()
    to_return = ServiceResponse(id=service.id, name= service.name, no_of_counters=service.no_of_counters)
    try:
    # Find the service by ID
        counters_to_del = (
            db.query(Counter)
            .filter(Counter.service_id==service_id)
            .all()
        )

        if not service:
            raise HTTPException(status_code=StatusCode.NOT_FOUND.value, detail=StatusCode.NOT_FOUND.message)

        # Check if there are active users in the service queues before deletion
        active_users = db.query(UserData).filter(UserData.service_id == service_id).count()

        if active_users > 0:
            logging.debug(f"delete_service failed: there are active users in the service {service_id}")
            raise HTTPException(status_code=StatusCode.BAD_REQUEST.value, detail=StatusCode.BAD_REQUEST.message)
        
        # Remove service from global queue
        del settings.counters[service_id]

        # Delete the service from DB
        try:
            db.delete(service)
            for items in counters_to_del:
                db.delete(items)
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            logging.error(f"failed delete_service: {str(e)}")
            raise HTTPException(status_code=StatusCode.INTERNAL_SERVER_ERROR.value, detail=StatusCode.INTERNAL_SERVER_ERROR.message)
        return StatusResponse(status_code=StatusCode.OK.value,status_message= StatusCode.OK.message, data=to_return)

    except Exception as e:
        db.rollback()
        logging.error(f"Error deleting service: {str(e)}")
        raise HTTPException(status_code=StatusCode.INTERNAL_SERVER_ERROR.value, detail=StatusCode.INTERNAL_SERVER_ERROR.message)
