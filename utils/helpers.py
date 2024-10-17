import requests, re
from schema.distance_models import *
from fastapi import HTTPException
from sqlalchemy.orm import Session
from database.models import UserData, Counter#, Service
import time
from status import StatusCode
from utils.global_settings import (
    settings,
    DISTANCEMATRIX_API_KEY,
    Q_SOLUTIONS_COORDS
)
import logging
from utils.global_settings import settings, setup_logging

setup_logging()
logger = logging.getLogger(__name__)

logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)  # Only log errors for SQLAlchemy
logging.getLogger("sqlalchemy.pool").setLevel(logging.ERROR)

# Suppress logs from any other external library
logging.getLogger("uvicorn.access").setLevel(logging.ERROR)  # For FastAPI/Uvicorn access logs
logging.getLogger("uvicorn.error").setLevel(logging.ERROR)

# dependency
def clear_queue(db):
    """
    Clears the database by deleting all user data.

    Args:
        db (Session): A database session.

    Returns:
        None

    Notes:
        - This function is used to reset the database.
        - It permanently deletes all user data, so use with caution.
        - Mostly used for testing purposes.
    """
    # imported here to avoid circular imports
    logging.info("clearing database")
    from database.models import UserData
    db.query(UserData).delete()
    db.commit()

def get_ETA(location: Location):
    """
    Calculate the estimated time of arrival (ETA) for a user at a given location.

    This function uses the Distance Matrix API to calculate the travel time from the user's location to the Q Solutions coordinates.

    Args:
        location (Location): The user's location.

    Returns:
        int: The estimated time of arrival in minutes.

    Raises:
        HTTPException:
            - If there's an error during the API request (500).
    """    
    try:
        response = requests.get(
            f"https://api.distancematrix.ai/maps/api/distancematrix/json",
            params={
                "origins": f"{location.latitude},{location.longitude}",
                "destinations": f"{Q_SOLUTIONS_COORDS[0]},{Q_SOLUTIONS_COORDS[1]}",
                "key": DISTANCEMATRIX_API_KEY
            }
        )

        data = response.json()

        if "rows" in data and data["rows"]:
            # distance = data["rows"][0]["elements"][0]["distance"]["text"]
            duration_str = data["rows"][0]["elements"][0]["duration"]["text"]
            logging.debug(f"duration string: {duration_str}")
            
            duration_match = re.search(r'(?:(\d+)\s*hour[s]?)?\s*(?:(\d+)\s*min[s]?)?', duration_str)
            if duration_match:
                hours = int(duration_match.group(1)) if duration_match.group(1) else 0  
                minutes = int(duration_match.group(2)) if duration_match.group(2) else 0

                duration_in_minutes = (hours*60) + minutes
                return duration_in_minutes
        # else:
            # raise HTTPException(status_code=500, detail="Failed to calculate ETA")

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to calculate ETA "+str(e))
    

async def check_if_serving(counter_id: int, db:Session):
    """
    Check if a counter is currently serving a user.

    This function checks if a counter is currently serving a user by checking if the first user in the queue has an ETA of 0.

    Args:
        counter_id (int): The ID of the counter to check.
        db (Session): A database session.

    Raises:
        HTTPException:
            - If there are no users in the counter (400).
    """
    users= (
        db.query(UserData)
        .filter(UserData.counter == counter_id)
        .order_by(UserData.pos)
        .all()
    )
    if users:
        first_user = users[0]
        if first_user.ETA == 0:
            first_user.processing_time = time.time()
            if users.count() > 1:
                settings.is_empty = False
            else: 
                settings.is_empty = True
    else:
        raise HTTPException(status_code=400, detail=f"No users in counter {counter_id}")

async def is_here(counter_id:int, db: Session):
    """
    Check if the first user in the queue for a specific counter has arrived.

    This function checks if the first user in the queue for the specified counter has an ETA of 0,
    indicating that they have arrived at the counter.

    Args:
        counter_id (int): The ID of the counter to check.
        db (Session): A database session.

    Returns:
        bool: True if the first user has arrived (ETA = 0), False otherwise.

    Raises:
        HTTPException:
            - If the counter is empty (404).
            - If the counter ID is invalid (400).
    """
    if Counter.id == counter_id:
        first_user= (
            db.query(UserData)
            .filter(UserData.counter == counter_id)
            .order_by(UserData.pos)
            .first()   
        )
        # processing_counter= (
        #     db.query(Counter)
        #     .filter(Counter.id == counter_id)
        #     .first()
        # )
        if first_user:
            if first_user.ETA == 0:
                return True
            else:
                return False
        else:
            raise HTTPException(status_code=StatusCode.NOT_FOUND.value, detail=StatusCode.NOT_FOUND.message)
    else:
        raise HTTPException(status_code=StatusCode.BAD_REQUEST.value, detail=StatusCode.BAD_REQUEST.message)

async def rebalance_q(service_id:int, db:Session):
    """
    Rebalance the queue for a specific service.

    This function rebalances the queue for the specified service by moving users from the counter with the longest queue to the counter with the shortest queue.

    Args:
        service_id (int): The ID of the service to rebalance.
        db (Session): A database session.

    Returns:
        None

    Notes:
        - This function assumes that the service has at least two counters.
        - It moves users from the counter with the longest queue to the counter with the shortest queue until the queues are balanced.
    """
    service_counters = settings.counters[service_id]
    if len(service_counters) > 1:
        
        min_queue = min(service_counters.values())
        shortest_queues = [counter for counter, users in service_counters.items() if users == min_queue]
        _minQ = shortest_queues[0]  # Select the first counter with the least number of users
        min_counter = (
            db.query(Counter)
            .filter(Counter.id == _minQ)
            .first()
        )

        max_queue = max(service_counters.values())
        longest_queues = [counter for counter, users in service_counters.items() if users==max_queue]
        _maxQ = longest_queues[0]
        max_counter = (
            db.query(Counter)
            .filter(Counter.id == _maxQ)
            .first()
        )

        if (min_counter and max_counter) and max_counter.in_queue > min_counter.in_queue + 1:
            min_est = min_counter.avg_tat * min_counter.in_queue
            # this will give us the position of the user to move
            position_to_move = round(min_est / max_counter.avg_tat) + 1

            user_rebalance= (
                db.query(UserData)
                .filter(UserData.counter == max_counter.id, UserData.pos == position_to_move)
                .first()
            )
            user_rebalance.counter = min_counter.id
            max_counter.in_queue -= 1
            min_counter.in_queue += 1

            reorder_max= (
                db.query(UserData)
                .filter(UserData.counter == max_counter.id)
                .order_by(UserData.pos)
                .all()
            )
            for index, user in enumerate(reorder_max, start=1):
                user.pos = index

            reorder_min= (
                db.query(UserData)
                .filter(UserData.counter == min_counter.id)
                .order_by(UserData.pos)
                .all()      
            )
            for index, user in enumerate(reorder_min, start=1):
                user.pos = index