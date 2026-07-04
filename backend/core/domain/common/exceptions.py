from __future__ import annotations

from typing import Any


class DomainException(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class EntityNotFound(DomainException):
    """Raised when a requested entity does not exist."""

    def __init__(
        self, entity_type: str, identifier: str | int, **kwargs: Any
    ) -> None:
        super().__init__(
            message=f"{entity_type} with identifier '{identifier}' not found",
            details={"entity_type": entity_type, "identifier": str(identifier), **kwargs},
        )


class ValidationException(DomainException):
    """Raised when domain invariants or input validation fails."""

    def __init__(
        self,
        message: str,
        field_errors: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message=message,
            details={"field_errors": field_errors or {}, **kwargs},
        )


class DuplicateEntityException(DomainException):
    """Raised when an entity with a unique constraint already exists."""

    def __init__(
        self,
        entity_type: str,
        identifier: str | int,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message=f"{entity_type} with identifier '{identifier}' already exists",
            details={"entity_type": entity_type, "identifier": str(identifier), **kwargs},
        )


class UnauthorizedError(DomainException):
    """Raised when an operation is not permitted."""

    def __init__(
        self,
        message: str = "You do not have permission to perform this operation",
        **kwargs: Any,
    ) -> None:
        super().__init__(message=message, details=kwargs)
