from utils.helpers import rebalance_q
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import Services, UserData, Counters
import logging
from utils.global_settings import settings
import time

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs\\q_system.log', mode='w')
    ]
)

router = APIRouter(
    prefix="/operator",
    tags= ["operator"]
)

def create_response(data = None, success = True, error = None):
    return{
        'success':success,
        'data': data,
        'error':error
    }


@router.get("/service", response_model=None)
async def select_services(db:Session = Depends(get_db)):
    try:
        services = db.query(Services).all()
        return create_response(data=services)
    except Exception as e:
        raise HTTPException(status_code=500, detail=create_response(success= False, error={'message': str(e)}))

@router.post("/select_counter")
async def select_counter(service_id: int):
    global settings
    try:
        return create_response(data={"counters": settings.counters[service_id]}) 
    except Exception as e:
        raise HTTPException(status_code=500, detail=create_response(success=False, error={'message':f'counters for the selected service: {settings.counters}'}))            

@router.get("/queue")
async def get_queue(service_id : int, counter: int, db:Session = Depends(get_db)):
    service=  db.query(Services).filter(Services.id == service_id).first()
    if service:    
        queue=(
            db.query(UserData)
            .filter(UserData.service_id == service_id, UserData.counter == counter)
            .order_by(UserData.pos)
            .all()
        )
        print(f"Queue for service {service_id}, counter {counter}: {queue}")
        
        if not queue:
            return create_response(data=["queue is empty"], success=True, error=None)
        return create_response(data=queue)
    else:
        raise HTTPException(status_code=500, detail=create_response(success=False, error={'message': 'Internal Error'}))              

@router.delete("/pop_user")
async def pop_next_user(service_id: int, counter: int, db: Session= Depends(get_db)):
    # finding the user at position 1
    service = db.query(Services).filter(Services.id == service_id).first()
    if service:
        users = (
            db.query(UserData)
            .filter(UserData.service_id == service_id, UserData.counter == counter)
            .order_by(UserData.pos)
            .all()
        )
        if not users:
            return create_response(success=False, error={'message': 'No users found'})
        _q = (
            db.query(Counters)
            .filter(Counters.id == counter)
            .first()
        )
        first_user = users[0]
        if first_user:
            # deleting the first user 
            if first_user:
                _q.in_queue -=1
                _q.users_processed +=1
                _q.total_tat = time.time() - _q.total_tat
                _q.avg_tat = _q.total_tat/ _q.users_processed
                try:
                    # db.add()
                    db.commit()
                except Exception as e:
                    db.rollback()
                    raise HTTPException(status_code=500, detail=f"Cant process time for user {first_user} because {str(e)}")
                db.delete(first_user)
                db.commit()
                settings.counters[service_id][counter] -= 1 # decrementing the number of users in the counters dictionary 
                logging.debug(f"popped user {first_user.id}, from counter {counter}")
            
                remaining_users = (
                    db.query(UserData)
                    .filter(UserData.service_id == service_id, UserData.counter == counter)
                    .order_by(UserData.ETA)
                    .all()
                )
                if remaining_users:
                    settings.is_empty = False
                
                # reassigning indices 
                for index, user in enumerate(remaining_users, start=1):
                    user.pos = index
                db.commit()
                logging.debug(f"Rescheduled counter {counter}, updated Queue: {remaining_users}")

                rebalance_q(service_id, db)

                return create_response(data={'message':f'Popped User, Rescheduled and Rebalanced the counters in Sevice no.{service_id}'})
            else:
                return create_response(success= False, data={'message':"No Users To Pop"})
    else: 
        # logging.error(f"Error while popping user {first_user.id}")
        db.rollback()
        raise HTTPException(status_code=404, detail=create_response(success=False, error={'message':'Service not found'}))