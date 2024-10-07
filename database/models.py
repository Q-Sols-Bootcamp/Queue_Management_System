from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database.db import Base, engine  # Assuming db.py contains the Base and engine objects
from passlib.context import CryptContext

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated= "auto")

class UserData(Base):
    __tablename__ = "user_data"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable= False, index=True)
    hashed_password = Column(String(100), nullable= False)
    counter = Column(Integer, ForeignKey('counter.id'), default=None)  
    pos = Column(Integer, default=None)
    ETA = Column(Integer, default= 0)
    service_id = Column(Integer, ForeignKey('services.id'))
    # processing_time= Column(Integer, nullable=True)
    # Correct relationship to the Service model
    service = relationship("Services", back_populates="users")  # Single service, not services
    counter_ = relationship("Counters", back_populates="users")


class Services(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    no_of_counters = Column(Integer, nullable=False, default=0)

    # Correct corresponding relationship to the UserData model
    users = relationship("UserData", back_populates="service")  # Use 'service' here to match UserData
    counter_ = relationship("Counters", back_populates= "service")
    
class Counters(Base):
    __tablename__ = "counter"
    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey('services.id'))
    avg_tat = Column(Integer, default= 0)
    total_tat = Column(Integer, default= 0)
    users_processed = Column(Integer, default= 0)
    in_queue = Column(Integer, default= 0)

    service = relationship("Services", back_populates="counter_")
    users = relationship("UserData", back_populates="counter_")
    
    
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
