from schema.distance_models import *
from pydantic_settings import BaseSettings
import logging, os
from logging.handlers import RotatingFileHandler
import os 
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    counters:dict = {}
    uid: int = 0

    is_empty: bool = True
    global_counter: int = 1

    
settings = Settings()

DISTANCEMATRIX_API_KEY = os.getenv('DISTANCEMATRIX_API_KEY')
Q_SOLUTIONS_COORDS = (24.85265469425946, 67.00765930367423)


def setup_logging():
    log_file_path = os.path.join('logs', 'q_system.log')

    handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        mode='a'
    )
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

     # Set the default logging level
    logging.getLogger().setLevel(logging.DEBUG)

    # Add the handler to the root logger
    logging.getLogger().addHandler(handler)