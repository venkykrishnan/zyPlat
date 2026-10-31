"""Unit tests for the typed exception taxonomy."""

import pytest

from backend.app.core.exceptions import (
    AuthorizationError,
    ConflictError,
    InfrastructureError,
    NotFoundError,
    ValidationError,
    ZyPlatError,
)


class TestExceptionTaxonomy:
    """Every error type needs a stable, distinct machine-readable code."""

    @pytest.mark.parametrize(
        ("error_type", "expected_code"),
        [
            (NotFoundError, "not_found"),
            (ConflictError, "conflict"),
            (ValidationError, "validation_error"),
            (AuthorizationError, "forbidden"),
            (InfrastructureError, "infrastructure_error"),
        ],
    )
    def test_error_type_has_stable_code(self, error_type, expected_code):
        """Clients and the central error handler depend on these codes never changing."""
        error = error_type("boom")

        assert error.code == expected_code
        assert isinstance(error, ZyPlatError)

    def test_error_keeps_message_and_details(self):
        """Details carry one entry per problem so APIs can report all of them at once."""
        error = ValidationError("bad frame", details=["column a", "column b"])

        assert error.message == "bad frame"
        assert str(error) == "bad frame"
        assert error.details == ["column a", "column b"]

    def test_details_default_to_empty_list_not_shared(self):
        """A shared mutable default would leak details between unrelated errors."""
        first = NotFoundError("one")
        second = NotFoundError("two")
        first.details.append("only on first")

        assert second.details == []
