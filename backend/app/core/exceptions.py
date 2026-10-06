from typing import Any, Optional


class AppException(Exception):
    """Base application exception with status code, error code, and detailed message."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "BAD_REQUEST",
        data: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.data = data


class ResourceNotFoundException(AppException):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} with identifier '{identifier}' was not found.",
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
        )


class DuplicateResourceException(AppException):
    def __init__(self, resource: str, field: str, value: Any):
        super().__init__(
            message=f"{resource} with {field} '{value}' already exists.",
            status_code=409,
            error_code="DUPLICATE_RESOURCE",
        )


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication credentials were not provided or are invalid."):
        super().__init__(
            message=message,
            status_code=401,
            error_code="UNAUTHORIZED",
        )


class InvalidCredentialsException(AppException):
    def __init__(self, message: str = "Invalid email or password."):
        super().__init__(
            message=message,
            status_code=401,
            error_code="INVALID_CREDENTIALS",
        )


class ForbiddenException(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN",
        )


class HospitalAccessDeniedException(AppException):
    def __init__(self, message: str = "Access to resources from another hospital is denied."):
        super().__init__(
            message=message,
            status_code=403,
            error_code="HOSPITAL_ACCESS_DENIED",
        )


class ValidationException(AppException):
    def __init__(self, message: str, data: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            data=data,
        )
