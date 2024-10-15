from pydantic import BaseModel
from typing import Optional, Any
from enum import Enum


class StatusCode(Enum):
    OK = (200, "OK")
    CREATED = (201, "Created")
    BAD_REQUEST = (400, "Bad Request")
    UNAUTHORIZED = (401, "Unauthorized")
    NOT_FOUND = (404, "Not Found")
    CONFLICT = (409, "Conflict")
    INTERNAL_SERVER_ERROR = (500, "Internal Server Error")

    def __init__(self, code, message):
        self._value_ = code
        self.message = message


class StatusResponse(BaseModel):
    status_code: int
    status_message: str
    data: Optional[Any] = None
