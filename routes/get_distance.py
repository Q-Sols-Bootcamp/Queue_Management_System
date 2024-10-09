import time
from fastapi import APIRouter, Depends, HTTPException, HTTPException, Depends
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import UserData, Counters
import re
import logging
import requests
from schema.distance_models import *
from utils.helpers import is_here


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs\\q_system.log', mode='w')
    ]
)

router = APIRouter(
    prefix="/distance",
    tags=["distance"]
)
def create_response(data= None, success= True, error= None):
    return{
        "data":data,
        "success": success,
        "error": error 
    }


# Predefined coordinates (Q-Solutions)
# Q_SOLUTIONS_COORDS = (24.943884886081435, 67.13863447171319) //dow uni coords
DISTANCEMATRIX_API_KEY = 'Lr2WU4gVeOw3jGXiy5AXTZAbt2raCLdnsPAZnvcnqjLYoYE6mgfwIrPMY4Hmhh2J'
Q_SOLUTIONS_COORDS = (24.85265469425946, 67.00765930367423)

@router.put("")
async def update_eta(request: UpdateEtaReaquest, db: Session = Depends(get_db)):
    try:
        response = requests.get(
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
                raise HTTPException(status_code=500, detail="Failed to parse ETA from distance API response")
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
            raise HTTPException(status_code=404, detail=f"User not found")

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
        raise HTTPException(status_code=404, detail=f"Failed to Update ETA")
    
    get_counter= (
        db.query(UserData.counter)
        .filter(UserData.id == request.userid)
        .first() # or use .scalar() to directly use the value instead of extracting it out of the tuple
    )
    counter_id = get_counter[0]
    if is_here(counter_id=counter_id, db=db) == True:
        processing_counter= (
            db.query(Counters)
            .filter(Counters.id == counter_id)
            .first()
        )
        processing_counter.total_tat = time.time() - processing_counter.total_tat
        try:
            # db.add()
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Can not start processing time for counter no{counter_id} because {str(e)}")
    return create_response(data={"message": "ETA updated successfully"}, success= True)
