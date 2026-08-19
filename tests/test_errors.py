import pytest

from yasin_mcp.errors.errors import (
    ErrorCategory,
    InternalError,
    McpError,
    NotFoundError,
    PolicyDeniedError,
    RateLimitedError,
    TimeoutMcpError,
    UnauthenticatedError,
    UnauthorizedError,
    UnavailableDependencyError,
    UpstreamError,
    ValidationError,
)


def test_mcp_error_construction():
    err = McpError(category=ErrorCategory.NOT_FOUND, message="not found")
    assert err.category == ErrorCategory.NOT_FOUND
    assert err.message == "not found"
    assert err.details == {}


def test_mcp_error_rejects_empty_message():
    with pytest.raises(ValueError):
        McpError(category=ErrorCategory.NOT_FOUND, message="")


def test_mcp_error_str_includes_category_and_message():
    err = McpError(category=ErrorCategory.TIMEOUT, message="took too long")
    assert "timeout" in str(err)
    assert "took too long" in str(err)


def test_mcp_error_is_raisable_and_catchable():
    with pytest.raises(McpError):
        raise McpError(category=ErrorCategory.INTERNAL_ERROR, message="boom")


@pytest.mark.parametrize(
    "error_class,expected_category",
    [
        (ValidationError, ErrorCategory.VALIDATION_ERROR),
        (NotFoundError, ErrorCategory.NOT_FOUND),
        (UnauthenticatedError, ErrorCategory.UNAUTHENTICATED),
        (UnauthorizedError, ErrorCategory.UNAUTHORIZED),
        (RateLimitedError, ErrorCategory.RATE_LIMITED),
        (TimeoutMcpError, ErrorCategory.TIMEOUT),
        (UnavailableDependencyError, ErrorCategory.UNAVAILABLE_DEPENDENCY),
        (UpstreamError, ErrorCategory.UPSTREAM_ERROR),
        (PolicyDeniedError, ErrorCategory.POLICY_DENIED),
        (InternalError, ErrorCategory.INTERNAL_ERROR),
    ],
)
def test_convenience_subclasses_set_correct_category(error_class, expected_category):
    err = error_class("some message")
    assert err.category == expected_category


def test_convenience_subclass_accepts_details():
    err = NotFoundError("missing", details={"id": "123"})
    assert err.details == {"id": "123"}


def test_convenience_subclass_is_instance_of_mcp_error():
    err = ValidationError("bad input")
    assert isinstance(err, McpError)


def test_all_error_categories_distinct():
    values = [c.value for c in ErrorCategory]
    assert len(values) == len(set(values))
