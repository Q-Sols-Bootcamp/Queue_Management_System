from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database.db import Base, engine  # Assuming db.py contains the Base and engine objects
from passlib.context import CryptContext

class UserData(Base):

    """
        Represents a user in the queue management system.
        Attributes:
            id (int): Primary key.
            name (str): Unique username.
            hashed_password (str): Hashed user password.
            counter (int): Foreign key to Counter.
            pos (int): Position in the queue.
            ETA (int): Estimated Time of Arrival.
            service_id (int): Foreign key to Service.
   """


    __tablename__ = "user_data"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable= False, index=True)
    hashed_password = Column(String(100), nullable= False)
    counter = Column(Integer, ForeignKey('counters.id'), default=None, nullable=False, index= True)
    pos = Column(Integer, default=None, nullable= False)
    ETA = Column(Integer, default= 0)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False, index= True)
    processing_time= Column(Integer, nullable=True, default=0)
    # Correct relationship to the Service model
    service = relationship("Service", back_populates="users")  # Single service, not services
    counter_rel = relationship("Counter", back_populates="users")


class Service(Base):

    """
        Represents a service in the queue management system.
        Attributes:
            id (int): Primary key.
            name (str): Unique service name.
            no_of_counters (int): Number of counters present in the service.            
   """    
    
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    no_of_counters = Column(Integer, nullable=False, default=0)

    # Correct corresponding relationship to the UserData model
    users = relationship("UserData", back_populates="service")  # Use 'service' here to match UserData
    counter_rel = relationship("Counter", back_populates= "service")
    
class Counter(Base):
    """
    Represents a counter in the queue management system.
    Attributes:
        id (int): Primary key.
        service_id(int): Foreign key to Service.
        avg_tat(int): Average Processing(Turn-Around-Time) time of the counter.
        total_tat(int): Total Processing(Turn-Around-Time) of the counter.
        users_processed(int): Number of users processed by the counter.
        in_queue(int): Number of users in the queue of the counter.
    """
    
    
    __tablename__ = "counters"
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey('services.id'), index= True)
    avg_tat = Column(Integer, default= 0)
    total_tat = Column(Integer, default= 0)
    users_processed = Column(Integer, default= 0)
    in_queue = Column(Integer, default= 0)

    service = relationship("Service", back_populates="counter_rel")
    users = relationship("UserData", back_populates="counter_rel")
    
    
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
