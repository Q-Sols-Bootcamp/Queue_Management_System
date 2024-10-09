from pydantic import BaseModel

class Location(BaseModel):
    latitude: float 
    longitude: float

class UpdateEtaReaquest(BaseModel):
    userid: int
    location: Location 
