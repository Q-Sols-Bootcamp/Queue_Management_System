from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
import os
from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")

#creating new engine instance to interact with the database and session object
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#base class for all models to inherit from
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
