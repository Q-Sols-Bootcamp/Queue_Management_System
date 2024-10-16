from pydantic import BaseModel

class Location(BaseModel):
    latitude: float 
    longitude: float

class UpdateEtaReaquest(BaseModel):
    userid: int
    location: Location 

class UpdateUserResponse(BaseModel):
    userid: int
    update_eta: int
