"""Machine-readable protocol-boundary error payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from yasin_mcp.errors.errors import McpError


@dataclass(frozen=True)
class ErrorResponse:
    """Safe wire-oriented representation of an internal MCP error."""

    code: str
    message: str
    details: dict[str, Any]

    @classmethod
    def from_error(cls, error: McpError) -> ErrorResponse:
        """Convert a structured error without exposing exception internals."""
        return cls(
            code=error.category.value,
            message=error.message,
            details=dict(error.details),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": dict(self.details),
            }
        }
