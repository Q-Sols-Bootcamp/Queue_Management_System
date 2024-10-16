from utils.helpers import rebalance_q
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schema.operator_models import SelectQueue, UserDataResponse
from database.db import get_db
from database.models import Service, UserData, Counter
import time, logging
from status import StatusCode, StatusResponse
from utils.global_settings import settings, setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# logging.debug("This is a debug message from my module.")

router = APIRouter(
    prefix="/operator",
    tags= ["operator"]
)

@router.get("/service")
async def get_services(db:Session = Depends(get_db)):
    """
    Retrieve a list of all services.

    This endpoint returns a list of all services in the system.

    Args:
        db (Session, optional): A database session. Defaults to Depends(get_db).

    Returns:
        StatusResponse: A response object containing a list of services.

    Raises:
        HTTPException:
            - If there's an error during the retrieval process (500).
    """
    try:
        services = db.query(Service).all()
    except Exception as e:
        logging.debug(f"get_services failed because {str(e)}")
        raise HTTPException(status_code=StatusCode.INTERNAL_SERVER_ERROR.value, detail=StatusCode.INTERNAL_SERVER_ERROR.message)
    return (services)

@router.get("/counters/{service_id}")
async def get_counter(service_id: int, db:Session=Depends(get_db)):
    """
    Retrieve the counter information for a service.

    This endpoint returns the counter information for a specific service.

    Args:
        service_id (int): The ID of the service.

    Returns:
        StatusResponse: A response object containing the counter information.

    Raises:
        HTTPException:
            - If the service ID is invalid or not found (400).
            - If there's an error during the retrieval process (500).
    """
    try:
        counters = db.query(Counter).filter(Service.id == service_id).all()
        # return {"counters": settings.counters[service_id]}
        return {"counters": counters}
    except Exception as e:
        logging.debug(f"get_counter failed: {str(e)}")
        raise HTTPException(status_code=StatusCode.BAD_REQUEST.value, detail=StatusCode.BAD_REQUEST.message)

@router.get("/queue/{counter_id}")
async def get_queue(counter_id:int, db:Session = Depends(get_db)):
    """
    Retrieve the queue information for a specific service and counter.

    This endpoint returns the queue information for a specific service and counter.

    Args:
        request (SelectQueue): A request object containing the service ID and counter.
        db (Session, optional): A database session. Defaults to Depends(get_db).

    Returns:
        A response object containing the queue information.

    Raises:
        HTTPException:
            - If the service ID is not found (404).
            - If there's an error during the retrieval process (500).
    """
    check_service= db.query(Counter.service_id).filter(Counter.id==counter_id).first()
    if check_service is None:
        raise HTTPException(status_code=StatusCode.NOT_FOUND.value, detail=StatusCode.NOT_FOUND.message)

    try:
        queue= db.query(UserData).filter(UserData.counter==counter_id).all()
        return (queue)
    except Exception as e:
        logging.debug(f"Failed get_queue(): {str(e)}")
        raise HTTPException(status_code=StatusCode.INTERNAL_SERVER_ERROR.value, detail=StatusCode.INTERNAL_SERVER_ERROR.message)

@router.post("/queue/next")
async def pop_next_user_from_queue(request: SelectQueue, db: Session= Depends(get_db)):
    """
    Pop the next user from the queue for a specific service and counter.

    This endpoint removes the next user from the queue for a specific service and counter.

    Args:
        request (SelectQueue): A request object containing the service ID and counter.
        db (Session, optional): A database session. Defaults to Depends(get_db).

    Returns:
        StatusResponse: A response object indicating the success or failure of the operation.

    Raises:
        HTTPException:
            - If the service ID is invalid or not found (400).
            - If there's an error during the retrieval process (500).
            - If the queue is empty (404).
    """    
    # finding the user at position 1
    service = db.query(Service).filter(Service.id == request.service_id).first()
    if service:
        users = (
            db.query(UserData)
            .filter(UserData.service_id == request.service_id, UserData.counter == request.counter)
            .order_by(UserData.pos)
            .all()
        )
        if not users:
            raise HTTPException(status_code=StatusCode.NOT_FOUND.value, detail=StatusCode.NOT_FOUND.message)
        _q = (
            db.query(Counter)
            .filter(Counter.id == request.counter)
            .first()
        )
        first_user = users[0]
        if first_user:
            # deleting the first user 
            if first_user:
                _q.in_queue -=1
                _q.users_processed +=1
                # add processing time to the user 
                first_user.processing_time = time.time() - first_user.processing_time
                # add the user processing time to the counters total processing time
                _q.total_tat = _q.total_tat + first_user.processing_time
                _q.avg_tat = _q.total_tat/ _q.users_processed
                try:
                    # db.add()
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logging.debug(f"pop_next_user_from_queue failed because: {str(e)} ")
                    raise HTTPException(status_code=StatusCode.INTERNAL_SERVER_ERROR.value, detail=StatusCode.INTERNAL_SERVER_ERROR.message)
                db.delete(first_user)
                db.commit()
                settings.counters[request.service_id][request.counter] -= 1 # decrementing the number of users in the counters dictionary 
                logging.debug(f"popped user {first_user.id}, from counter {request.counter}")
            
                remaining_users = (
                    db.query(UserData)
                    .filter(UserData.service_id == request.service_id, UserData.counter == request.counter)
                    .order_by(UserData.ETA)
                    .all()
                )
                if remaining_users:
                    settings.is_empty = False
                
                # reassigning indices 
                for index, user in enumerate(remaining_users, start=1):
                    user.pos = index
                db.commit()
                logging.debug(f"Rescheduled counter {request.counter}, updated Queue: {remaining_users}")

                rebalance_q(request.service_id, db)

                return StatusResponse(status_code=StatusCode.OK.value,status_message=StatusCode.OK.message)
            else:
                raise HTTPException(status_code=StatusCode.NOT_FOUND.value, detail=StatusCode.NOT_FOUND.message)
    else: 
        logging.error(f"Error while popping user, service not found")
        db.rollback()
        raise HTTPException(status_code=StatusCode.NOT_FOUND.value, detail=StatusCode.NOT_FOUND.message)
