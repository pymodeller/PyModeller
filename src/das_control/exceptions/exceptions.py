"""AUTO-GENERATED EXCEPTIONS."""

from collections.abc import Generator
from typing import Any
from starlette.exceptions import HTTPException


def generate_dict(description: str, detail: str, code: int) -> dict:
    """Generate dict."""
    return {
            "description": description,
            "content": {
                "application/json": {
                    "example": {"detail": detail, "code": code}
                }
            },
        }


class CustomException(HTTPException):
    """Custom exception."""

    def __init__(
        self,
        status_code: int = 500,
        detail: str = "General exception.",
        description: str = "General exception raised.",
    ) -> None:
        """Initialize exception."""
        super().__init__(status_code=status_code, detail=detail)
        self.code = status_code
        self.description = description

    def __iter__(self) -> Generator[tuple[str, Any]]:
        """Define iter method."""
        dict_ = generate_dict(self.description, self.detail, self.code)

        for key, value in dict_.items():
            yield key, value


class EntityNotFoundExceptionException(CustomException):
    """Raised when a database lookup by ID or unique field returns no results."""

    def __init__(
        self,
        status_code: int = 404,
        detail: str = "The requested resource was not found.",
        description: str = "Raised when a database lookup by ID or unique field returns no results.",
    ) -> None:
        """Initialize exception."""
        super().__init__(status_code=status_code, detail=detail, description=description)


class UnauthorizedExceptionException(CustomException):
    """Raised when the Bearer token is missing, expired, or invalid."""

    def __init__(
        self,
        status_code: int = 401,
        detail: str = "Could not validate credentials.",
        description: str = "Raised when the Bearer token is missing, expired, or invalid.",
    ) -> None:
        """Initialize exception."""
        super().__init__(status_code=status_code, detail=detail, description=description)


class ForbiddenExceptionException(CustomException):
    """Raised when the user is authenticated but lacks the required scopes or roles."""

    def __init__(
        self,
        status_code: int = 403,
        detail: str = "You do not have sufficient permissions.",
        description: str = "Raised when the user is authenticated but lacks the required scopes or roles.",
    ) -> None:
        """Initialize exception."""
        super().__init__(status_code=status_code, detail=detail, description=description)


class ValidationExceptionException(CustomException):
    """Raised when business logic validation fails (e.g., date ranges, unique constraints)."""

    def __init__(
        self,
        status_code: int = 422,
        detail: str = "The provided data is invalid.",
        description: str = "Raised when business logic validation fails (e.g., date ranges, unique constraints).",
    ) -> None:
        """Initialize exception."""
        super().__init__(status_code=status_code, detail=detail, description=description)


class ConflictExceptionException(CustomException):
    """Raised during creation if a unique constraint (like email) is violated."""

    def __init__(
        self,
        status_code: int = 409,
        detail: str = "Resource already exists.",
        description: str = "Raised during creation if a unique constraint (like email) is violated.",
    ) -> None:
        """Initialize exception."""
        super().__init__(status_code=status_code, detail=detail, description=description)


class BadRequestExceptionException(CustomException):
    """General purpose error for bad client input."""

    def __init__(
        self,
        status_code: int = 400,
        detail: str = "The request is malformed or contains invalid parameters.",
        description: str = "General purpose error for bad client input.",
    ) -> None:
        """Initialize exception."""
        super().__init__(status_code=status_code, detail=detail, description=description)


class InternalDatabaseExceptionException(CustomException):
    """Raised when the database connection fails or an unexpected SQL error occurs."""

    def __init__(
        self,
        status_code: int = 500,
        detail: str = "An internal error occurred while processing the data.",
        description: str = "Raised when the database connection fails or an unexpected SQL error occurs.",
    ) -> None:
        """Initialize exception."""
        super().__init__(status_code=status_code, detail=detail, description=description)


class ExternalServiceExceptionException(CustomException):
    """Raised when an external API call (e.g., Payment Gateway, Keycloak) fails."""

    def __init__(
        self,
        status_code: int = 502,
        detail: str = "Error communicating with an upstream service.",
        description: str = "Raised when an external API call (e.g., Payment Gateway, Keycloak) fails.",
    ) -> None:
        """Initialize exception."""
        super().__init__(status_code=status_code, detail=detail, description=description)


class ServiceUnavailableExceptionException(CustomException):
    """Used for planned maintenance or circuit breaker triggers."""

    def __init__(
        self,
        status_code: int = 503,
        detail: str = "The service is temporarily overloaded or down for maintenance.",
        description: str = "Used for planned maintenance or circuit breaker triggers.",
    ) -> None:
        """Initialize exception."""
        super().__init__(status_code=status_code, detail=detail, description=description)


