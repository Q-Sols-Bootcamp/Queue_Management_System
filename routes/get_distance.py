import time
from fastapi import APIRouter, Depends, HTTPException, HTTPException, Depends
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import UserData, Counter
import os, re, httpx, logging
from dotenv import load_dotenv
from schema.distance_models import UpdateEtaReaquest
from utils.helpers import is_here
from utils.global_settings import setup_logging
from status import StatusCode, StatusResponse
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

setup_logging()
logging = logging.getLogger(__name__)

router = APIRouter(
    prefix="/distance",
    tags=["distance"]
)

# Predefined coordinates (Q-Solutions)
# Q_SOLUTIONS_COORDS = (24.943884886081435, 67.13863447171319) //dow uni coords
DISTANCEMATRIX_API_KEY = os.getenv('DISTANCEMATRIX_API_KEY')
Q_SOLUTIONS_COORDS = (24.85265469425946, 67.00765930367423)

@router.put("")
async def update_eta(request: UpdateEtaReaquest, db: Session = Depends(get_db)):
    """
    Update the ETA (Estimated Time of Arrival) for a user.

    This endpoint calculates the ETA based on the user's current location and updates it in the database.

    Args:
        request (UpdateEtaRequest): A request object containing the user ID and current location.
        db (Session, optional): A database session. Defaults to Depends(get_db).

    Returns:
        StatusResponse: A response object indicating the status of the ETA update.

    Raises:
        HTTPException:
            - If the user is not found (404).
            - If there's an error during the ETA calculation or update process (500).
    """
    try:
        response = await httpx.get(
            f"https://api.distancematrix.ai/maps/api/distancematrix/json",
            params={
                "origins": f"{request.location.latitude},{request.location.longitude}",
                "destinations": f"{Q_SOLUTIONS_COORDS[0]},{Q_SOLUTIONS_COORDS[1]}",
                "key": DISTANCEMATRIX_API_KEY
            }
        )

        data = response.json()

        if "rows" in data and data["rows"]:
            # distance = data["rows"][0]["elements"][0]["distance"]["text"]
            duration_str = data["rows"][0]["elements"][0]["duration"]["text"]
            
            # Extract the integer value from the duration string (e.g., "15 mins" -> 15)
            duration_match = re.search(r'(?:(\d+)\s*hour[s]?)?\s*(?:(\d+)\s*min[s]?)?', duration_str)
            if duration_match:
                hours = int(duration_match.group(1)) if duration_match.group(1) else 0
                minutes = int(duration_match.group(2)) if duration_match.group(2) else 0

                duration_in_minutes = (hours*60) + minutes
                logging.debug(f"user {request.userid} has an updated ETA of {duration_in_minutes}")
                # return duration_in_minutes
            else:
                raise HTTPException(status_code=StatusCode.INTERNAL_SERVER_ERROR.value, detail=StatusCode.INTERNAL_SERVER_ERROR.message)
        # logging.debug(f"---------------------------------out of loop here")

        user_to_update = (
            db.query(UserData)
            .filter(UserData.id == request.userid)
            .first()
            )
        # logging.debug(f"user to update = {user_to_update}")

        if user_to_update:
            logging.debug(f"old ETA for user {request.userid} = {user_to_update.ETA}")
            user_to_update.ETA = duration_in_minutes
            logging.debug(f"new ETA for user {request.userid} = {user_to_update.ETA}")

        else:
            raise HTTPException(status_code=StatusCode.NOT_FOUND.value, detail=StatusCode.NOT_FOUND.message)

        db.commit()
        db.refresh(user_to_update)
        logging.debug(f"user_to_update.counter = {user_to_update.counter}")
        
        users_in_counter = (
            db.query(UserData)
            .filter(UserData.counter == user_to_update.counter)
            .order_by(UserData.ETA)
            .all()
        )

        for new_pos, user in enumerate(users_in_counter, start=1):
            user.pos = new_pos
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=StatusCode.BAD_REQUEST.value, detail=StatusCode.BAD_REQUEST.message)
    
    get_counter= (
        db.query(UserData.counter)
        .filter(UserData.id == request.userid)
        .first() # or use .scalar() to directly use the value instead of extracting it out of the tuple
    )
    counter_id = get_counter[0]
    if is_here(counter_id=counter_id, db=db) == True:
        first_user= (
            db.query(UserData)
            .filter(UserData.counter == counter_id)
            .order_by(UserData.pos)
            .first()
        )
        first_user.processing_time = time.time() - first_user.processing_time
        try:
            # db.add()
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            logging.debug(f"Can not start processing time for counter no{counter_id} because {str(e)}")
            raise HTTPException(status_code=StatusCode.INTERNAL_SERVER_ERROR.message, detail=StatusCode.INTERNAL_SERVER_ERROR.message)
    return StatusResponse(StatusCode.OK.value, StatusCode.OK.message)