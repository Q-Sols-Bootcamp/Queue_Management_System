from pydantic import BaseModel
from typing import Optional, Any
from enum import Enum


class StatusCode(Enum):
    OK = (200, "OK")
    CREATED = (201, "Created")
    BAD_REQUEST = (400, "Bad Request")
    UNAUTHORIZED = (401, "Unauthorized")
    FORBIDDEN = (403, "Forbidden")
    NOT_FOUND = (404, "Not Found")
    CONFLICT = (409, "Conflict")
    INTERNAL_SERVER_ERROR = (500, "Internal Server Error")
    SERVICE_UNAVAILABLE = (503, "Service Unavailable")

    def __init__(self, code, message):
        self._value_ = code
        self.message = message


def map_http_status_to_enum(status_code):
    if status_code == 400:
        return StatusCode.BAD_REQUEST
    elif status_code == 401:
        return StatusCode.UNAUTHORIZED
    elif status_code == 403:
        return StatusCode.FORBIDDEN
    elif status_code == 404:
        return StatusCode.NOT_FOUND
    elif status_code == 503:
        return StatusCode.SERVICE_UNAVAILABLE
    else:
        return StatusCode.INTERNAL_SERVER_ERROR


class StatusResponse(BaseModel):
    status_code: int
    status_message: str
    data: Optional[Any] = None
