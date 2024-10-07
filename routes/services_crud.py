from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from database.models import UserData, Services, Counters
from database.db import get_db
import logging
from utils.global_settings import settings
from schema.services_models import *


router = APIRouter(
    prefix="/services",
    tags=["services"]
)

def create_response(data=None, success=True, error=None):
    return {
        'success': success,
        'data': data,
        'error': error
    }


@router.post("/service", response_model=None)
async def add_service(request: CreateServiceRequest, db: Session = Depends(get_db)):
    global settings  # Ensure we are modifying the global counters and global_counter
    _present= (
        db.query(Services)
        .filter(Services.name == request.name)
        .first()
    )
    if not _present:
    
        # Create a new service in the database
        new_service = Services(name=request.name, no_of_counters=request.no_of_counters)
        db.add(new_service)
        db.commit()  # Commit to assign an ID to new_service

        # for i in range(request.no_of_counters):
        #     new_counter = Counters(no_of_counters=request.no_of_counters)

        # Re-query the database to fetch the newly created service (to ensure service ID is available)
        _serviceid = new_service.id
        db.refresh(new_service)

        # Initialize counters for the new service
        service_counters = {}

        # Use global_counter to assign unique counter numbers across all services
        for _ in range(request.no_of_counters):
            service_counters[settings.global_counter] = 0  # No users in the counter at start
            logging.info(f"Assigned counter {settings.global_counter} to service {new_service.name}")
            new_counter = Counters(id=settings.global_counter, service_id = _serviceid)
            db.add(new_counter)
            db.commit()
            db.refresh(new_counter)
        
            settings.global_counter += 1  # Increment global counter for the next assignment

        # Add this service's counters to the global counters dictionary using the service ID
        settings.counters[new_service.id] = service_counters

        # Log the initialization
        logging.info(f"Initialized counters for service {new_service.name}: {service_counters}")
        logging.info(f"Global counters state after addition: {settings.counters}")

        return create_response(data={'message': 'Service created successfully', 'service_id': new_service.id})

    else:
        db.rollback()
        raise HTTPException(status_code=500, detail=create_response(success=False, error={'message': 'error adding service'}))



# Update service details (name and/or no_of_counters)
@router.put("/service", response_model=None)
async def update_service(request: UpdateServiceRequest, db: Session = Depends(get_db)):
    global settings
    try:
        # Find the service by ID
        service = db.query(Services).filter(Services.id == request.service_id).first()
        
        if not service:
            raise HTTPException(status_code=404, detail=create_response(success=False, error={'message': 'Service not found'}))

        # Check if there are active users in the service queues before updating
        active_users = db.query(UserData).filter(UserData.service_id == request.service_id).count()
        if active_users > 0:
            raise HTTPException(status_code=400, detail=create_response(success=False, error={'message': 'Service has active users in its queues.'}))

        # Update service name if provided
        if request.name:
            service.name = request.name

        # Update number of counters if provided
        if request.no_of_counters is not None:
            current_counters = len(settings.counters.get(service.id, {}))

            if request.no_of_counters != current_counters:
                # Adjust global queues (adding/removing counters)
                if request.no_of_counters > current_counters:
                    # Add new counters (initialize them with 0 users)
                    for i in range(current_counters + 1, request.no_of_counters + 1):
                        settings.counters[service.id][i] = 0  # Initialize new counter with 0 users
                        for _ in range(request.no_of_counters-current_counters):
                            new_counters = Counters(id=settings.global_counter, service_id = service.id)
                            try:
                                db.add(new_counters)
                                db.commit()
                                db.refresh(new_counters)
                            except Exception as e:
                                raise HTTPException(status_code=500, detail=f"Failed to add new counter: {settings.global_counter} because {str(e)}")
                        settings.global_counter += 1 # incrementing the global_counter variable that determines counter_id globally 
                else:
                    # Remove counters (ensure they are empty before removing)
                    for i in range(current_counters, request.no_of_counters, -1):
                        if settings.counters[service.id][i] > 0:
                            raise HTTPException(status_code=400, detail=create_response(success=False, error={'message': f'Counter {i} has active users'}))
                        del settings.counters[service.id][i]  # Safely remove the empty counter
                        try:
                            to_del = (
                                db.query(Counters)
                                .filter(Counters.id == i)
                                .first()
                            )
                            db.delete(to_del)
                        except:
                            db.rollback()
                            raise HTTPException(status_code=500, detail=f"Failed to delete counter: {settings.global_counter} from database.")
                        settings.global_counter -= 1 # decrementing the global_counter variable that determines counter_id globally 
            
            # Update the number of counters in the database (service model)
            service.no_of_counters = request.no_of_counters
            logging.info(f"Updating no_of_counters to {request.no_of_counters}")

        # Persist changes in the database
        try:
            db.add(service)
            db.commit()
            db.refresh(service)
            # Query again to check if the changes are reflected
            updated_service = db.query(Services).filter(Services.id == request.service_id).first()
            logging.info(f"Updated service has no_of_counters: {updated_service.no_of_counters}")
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update service: {str(e)}")

        return create_response(data={'message': 'Service updated successfully'})

    except Exception as e:
        db.rollback()
        logging.error(f"Error updating service: {str(e)}")
        raise HTTPException(status_code=500, detail=create_response(success=False, error={'message': str(e)}))



# Delete a service
@router.delete("/service", response_model=None)
async def delete_service(service_id: int, db: Session = Depends(get_db)):
    try:
        # Find the service by ID
        service = db.query(Services).filter(Services.id == service_id).first()
        counters_to_del = (
            db.query(Counters)
            .filter(Counters.service_id==service_id)
            .all()
        )

        if not service:
            raise HTTPException(status_code=404, detail=create_response(success=False, error={'message': 'Service not found'}))

        # Check if there are active users in the service queues before deletion
        active_users = db.query(UserData).filter(UserData.service_id == service_id).count()

        if active_users > 0:
            raise HTTPException(status_code=400, detail=create_response(success=False, error={'message': 'Service has active users in its queues.'}))

        # Remove service from global queue
        del settings.counters[service_id]

        # Delete the service from DB
        db.delete(service)
        for items in counters_to_del:
            db.delete(items)
        db.commit()

        return create_response(data={'message': 'Service deleted successfully'})

    except Exception as e:
        db.rollback()
        logging.error(f"Error deleting service: {str(e)}")
        raise HTTPException(status_code=400, detail=create_response(success=False, error={'message': 'Bad Request'}))
    
    
# @router.get("/select_service", response_model=None)
# async def read_services(db:Session = Depends(get_db)):
#     try:
#         services = db.query(Services).all()
#         return create_response(data=services)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=create_response(success= False, error={'message': str(e)}))