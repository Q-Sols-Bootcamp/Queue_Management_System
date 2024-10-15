from pydantic import BaseModel

class CreateServiceRequest(BaseModel):
    name: str
    no_of_counters: int

class UpdateServiceRequest(BaseModel):
    service_id: int
    name: str = None
    no_of_counters: int = None

class ServiceResponse(BaseModel):
    id: int
    name: str
    no_of_counters: int