from pydantic import BaseModel

class SelectQueue(BaseModel):
    service_id: int
    counter: int

