from fastapi import APIRouter, Depends, HTTPException, Depends
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import UserData, Counter
from schema.user_models import GenerateTokenRequest, UserLoginRequest
from utils.global_settings import settings
from utils.helpers import get_ETA, is_here
import time, logging
from auth import create_access_token, hash_password, verify_password
from status import StatusCode, StatusResponse
from utils.global_settings import settings, setup_logging

setup_logging()
logging = logging.getLogger(__name__)


router = APIRouter(
    prefix="/user",
    tags=["user"]
)

@router.post("/generate_token", response_model=StatusResponse)
async def generate_token(request: GenerateTokenRequest, db: Session = Depends(get_db)):
    """
    Generate a token for a new user.

    This endpoint generates a token for a new user, assigns them to a counter with the fewest users, 
    and updates the queue positions based on the user's ETA.

    Args:
        request (GenerateTokenRequest): A request object containing the user's name, password, 
                                        service ID, and location.
        db (Session, optional): A database session. Defaults to Depends(get_db).

    Returns:
        StatusResponse: A response object indicating the status of the token generation.

    Raises:
        HTTPException: If the request is invalid (e.g., missing name or password), 
                        if the user name is already taken, or if there is an internal server error.
    """
    if not request.name or not request.password:
        raise HTTPException(status_code=StatusCode.BAD_REQUEST.value, detail=StatusCode.BAD_REQUEST.message)

    # checking to see if name is already taken since name is a unique field also acting as a user name
    existing_user=(
        db.query(UserData)
        .filter(UserData.name == request.name)
        .first()
    )
    if existing_user:
        raise HTTPException(status_code=StatusCode.CONFLICT.value, detail= StatusCode.CONFLICT.message)
    
    hashed_password = hash_password(request.password)

    # Increment the global UID
    settings.uid += 1

    # Check if the service exists and retrieve the counters for the selected service
    if request.service_id not in settings.counters:
        raise HTTPException(status_code=StatusCode.BAD_REQUEST.value, detail=StatusCode.BAD_REQUEST.message)

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
            first_user= (
                db.query(UserData)
                .filter(UserData.counter == selected_counter)
                .order_by(UserData.pos)
                .first()
            )
            if first_user:
                first_user.processing_time = time.time() - first_user.processing_time
                try:
                    # db.add()
                    db.commit()
                except Exception as e:
                    db.rollback()
                    raise HTTPException(status_code=StatusCode.INTERNAL_SERVER_ERROR.value, detail=StatusCode.INTERNAL_SERVER_ERROR.message)
            else:
                raise HTTPException(status_code=StatusCode.INTERNAL_SERVER_ERROR.value, detail=StatusCode.INTERNAL_SERVER_ERROR.message)
        

        # Update the counters dictionary to reflect the newly added user
        settings.counters[request.service_id][selected_counter] += 1
        processing_counter= (
                db.query(Counter)
                .filter(Counter.id == selected_counter)
                .first()
            )
        processing_counter.in_queue +=1
        try:
            # db.add()
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=StatusCode.INTERNAL_SERVER_ERROR.value, detail=StatusCode.INTERNAL_SERVER_ERROR.message)
        
        logging.info(f"Updated counters: {settings.counters}")

    except Exception as e:
        db.rollback()  # Rollback if there are any errors
        logging.error(f"Failed to register user {request.name}: {str(e)}")
        raise HTTPException(status_code=StatusCode.INTERNAL_SERVER_ERROR.value, detail=StatusCode.INTERNAL_SERVER_ERROR.message)

    # Return a success message
    return (StatusCode.CREATED.value, StatusCode.CREATED.message)

@router.post("/login", response_model=StatusResponse)
async def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user and generate an access token.

    This endpoint verifies the user's credentials and, if valid, generates an access token for the user.

    Args:
        request (UserLoginRequest): A request object containing the user's name and password.
        db (Session, optional): A database session. Defaults to Depends(get_db).

    Returns:
        StatusResponse: A response object containing the access token, token type, username, 
                        counter number, and position in the queue.

    Raises:
        HTTPException: If the user is not found (404) or if the credentials are invalid (401).
    """
    user= (
        db.query(UserData)
        .filter(UserData.name == request.name)
        .first()
    )
    if not user:
        raise HTTPException(status_code=StatusCode.NOT_FOUND.value, detail=StatusCode.NOT_FOUND.message)

    user = (
        db.query(UserData)
        .filter(UserData.name == request.name)
        .first()
    )

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data= {"subject": user.name})

    return StatusResponse(
        StatusCode.OK.value,
        StatusCode.OK.message,
        [{"access_token": access_token, "token_type":"bearer"}, {'username': user.name, 'counter number': user.counter, 'position':user.pos}],
    )