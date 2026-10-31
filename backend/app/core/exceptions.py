"""Typed exceptions for service and repository layers.

HTTP status mapping belongs in ``api/error_handlers.py``, never in these classes.
"""

from __future__ import annotations

from collections.abc import Sequence


class ZyPlatError(Exception):
    """Base class for all application errors.

    Attributes:
        code: Stable machine-readable error code.
        details: Optional list of specific problems (for example one entry per bad column).
    """

    code = "internal_error"

    def __init__(self, message: str, *, details: Sequence[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: list[str] = list(details or [])


class NotFoundError(ZyPlatError):
    """A requested resource does not exist."""

    code = "not_found"


class ConflictError(ZyPlatError):
    """The request conflicts with current state, such as writing to an immutable snapshot."""

    code = "conflict"


class ValidationError(ZyPlatError):
    """Input violates a business or structural rule."""

    code = "validation_error"


class AuthorizationError(ZyPlatError):
    """The caller is not allowed to perform the operation."""

    code = "forbidden"


class InfrastructureError(ZyPlatError):
    """A backing system (database, file storage) failed."""

    code = "infrastructure_error"
