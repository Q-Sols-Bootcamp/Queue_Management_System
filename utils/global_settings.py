from schema.distance_models import *
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    counters:dict = {}
    uid: int = 0

    # is_empty: bool = True
    global_counter: int = 1

    
settings = Settings()

DISTANCEMATRIX_API_KEY = 'Lr2WU4gVeOw3jGXiy5AXTZAbt2raCLdnsPAZnvcnqjLYoYE6mgfwIrPMY4Hmhh2J'
Q_SOLUTIONS_COORDS = (24.85265469425946, 67.00765930367423)
