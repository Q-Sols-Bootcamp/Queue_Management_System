from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
# import pymysql
# pymysql.install_as_MySQLdb()

DATABASE_URL = "mysql+mysqlconnector://sqluser:password@localhost/mock_queue_db"

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
