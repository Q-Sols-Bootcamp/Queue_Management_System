from pydantic import BaseModel

class SelectQueue(BaseModel):
    service_id: int
    counter: int
    
class UserDataResponse(BaseModel):
    # define the attributes of the UserData object here
    id: int
    service_id: int
    counter: int
    pos: int
