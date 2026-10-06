from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field
from app.core.middleware import get_current_request_id

DataT = TypeVar("DataT")


class ErrorDetail(BaseModel):
    code: str
    details: Optional[Any] = None


class ApiResponse(BaseModel, Generic[DataT]):
    success: bool
    message: str
    data: Optional[DataT] = None
    requestId: str = Field(default_factory=get_current_request_id)
    error: Optional[ErrorDetail] = None


def success_response(
    data: Optional[Any] = None,
    message: str = "Operation completed successfully",
) -> dict:
    """Helper to return a success dictionary matching the standard envelope."""
    return {
        "success": True,
        "message": message,
        "data": data,
        "requestId": get_current_request_id(),
        "error": None,
    }


def error_response(
    message: str,
    error_code: str = "INTERNAL_SERVER_ERROR",
    details: Optional[Any] = None,
    data: Optional[Any] = None,
) -> dict:
    """Helper to return an error dictionary matching the standard envelope."""
    return {
        "success": False,
        "message": message,
        "data": data,
        "requestId": get_current_request_id(),
        "error": {
            "code": error_code,
            "details": details,
        },
    }
