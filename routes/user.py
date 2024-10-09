from fastapi import APIRouter, Depends, HTTPException, Depends
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import UserData#, settings
from schema.user_models import *
from schema.distance_models import *
from utils.global_settings import settings
from utils.helpers import *
import logging
from auth import *

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs\\q_system.log', mode='w')
    ]
)


router = APIRouter(
    prefix="/user",
    tags=["user"]
)
def create_response(data= None, success= True, error= None):
    return{
        "data":data,
        "success": success,
        "error": error 
    }


@router.post("/generate_token")
async def generate_token(request: GenerateTokenRequest, db: Session = Depends(get_db)):
    global settings
    
    if not request.name or not request.password:
        raise HTTPException(status_code=400, detail="Name and password are required")

    # checking to see if name is already taken since name is a unique field also acting as a user name
    existing_user=(
        db.query(UserData)
        .filter(UserData.name == request.name)
        .first()
    )
    if existing_user:
        raise HTTPException(status_code=422, detail= "Name already taken")
    
    hashed_password = hash_password(request.password)

    # Increment the global UID
    settings.uid += 1

    # Check if the service exists and retrieve the counters for the selected service
    if request.service_id not in settings.counters:
        raise HTTPException(status_code=400, detail=f"Invalid service selected: {request.service_id}")

    service_counters = settings.counters[request.service_id]
    logging.info(f"Service counters for service {request.service_id}: {service_counters}")

    # Find the counter with the fewest users
    min_queue = min(service_counters.values())
    shortest_queues = [counter for counter, users in service_counters.items() if users == min_queue]
    selected_counter = shortest_queues[0]  # Select the first counter with the least number of users

    logging.info(f"Selected counter for user {request.name}: {selected_counter}")

    # Save the new user to the UserData table
    new_user = UserData(name=request.name, hashed_password=hashed_password, counter=selected_counter, pos=0, service_id=request.service_id, ETA= get_ETA(request.location))

    try:
        db.add(new_user)
        db.commit()  # Commit to generate a valid user ID
        db.refresh(new_user)  # Refresh the user to fetch the latest state

        # Update queue position based on ETA
        # Fetch all users in the selected counter, sorted by ETA
        users_in_counter = (
            db.query(UserData)
            .filter(UserData.service_id == request.service_id, UserData.counter == selected_counter)
            .order_by(UserData.ETA)
            .all()
        )

        # Recalculate positions based on ETA
        for index, user in enumerate(users_in_counter, start=1):
            user.pos = index

        db.commit()  # Commit changes to save the updated positions

        if is_here(counter_id=selected_counter, db=db) == True:
            processing_counter= (
                db.query(Counters)
                .filter(Counters.id == selected_counter)
                .first()
            )
            if processing_counter:
                processing_counter.total_tat = time.time() - processing_counter.total_tat
                try:
                    # db.add()
                    db.commit()
                except Exception as e:
                    db.rollback()
                    raise HTTPException(status_code=500, detail=f"Can not start processing time for counter no{selected_counter} because {str(e)}")
            else:
                raise HTTPException(status_code=500, detail=f"No counter found with id {selected_counter}")
        

        # Update the counters dictionary to reflect the newly added user
        settings.counters[request.service_id][selected_counter] += 1
        processing_counter= (
                db.query(Counters)
                .filter(Counters.id == selected_counter)
                .first()
            )
        processing_counter.in_queue +=1
        try:
            # db.add()
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to increment in_queue value for {selected_counter} because {str(e)}")
        
        logging.info(f"Updated counters: {settings.counters}")

    except Exception as e:
        db.rollback()  # Rollback if there are any errors
        logging.error(f"Failed to register user {request.name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to register user: {new_user.name} because {str(e)}" )

    # Return a success message
    return create_response(data={'message': f"User {request.name} registered to counter {selected_counter} at position {new_user.pos}"})

@router.post("/login")
async def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):
    user= (
        db.query(UserData)
        .filter(UserData.name == request.name)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user = (
        db.query(UserData)
        .filter(UserData.name == request.name)
        .first()
    )

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data= {"subject": user.name})

    return create_response(data=[{"access_token": access_token, "token_type":"bearer"}, {'username': user.name, 'counter number': user.counter, 'position':user.pos}])
