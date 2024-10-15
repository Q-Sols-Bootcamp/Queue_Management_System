from schema.distance_models import Location
from pydantic import BaseModel

class GenerateTokenRequest(BaseModel):
    name: str
    password: str
    service_id: int
    location: Location

class UserLoginRequest(BaseModel):
    name: str
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    counter:int
    pos: int
    eta: int