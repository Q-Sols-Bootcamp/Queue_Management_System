from pydantic import BaseModel, Field
from typing import Annotated

PositiveInt = Annotated[int, Field(strict=True, gt=0, le=10)]

class CreateServiceRequest(BaseModel):
    name: str
    no_of_counters: PositiveInt

class UpdateServiceRequest(BaseModel):
    service_id: int
    name: str = None
    no_of_counters: PositiveInt = None

class ServiceResponse(BaseModel):
    id: int
    name: str
    no_of_counters: PositiveInt
