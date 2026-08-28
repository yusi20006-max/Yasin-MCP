"""Approval boundary for MUTATION capabilities (Stage 11 / Issue #97)."""

from yasin_mcp.approval.constants import APPROVAL_PRESENT_ENV, APPROVAL_TOKEN_KWARG
from yasin_mcp.approval.store import InMemoryApprovalStore
from yasin_mcp.approval.types import ApprovalGrant, ApprovalStatus, ApprovalValidationResult

__all__ = [
    "APPROVAL_PRESENT_ENV",
    "APPROVAL_TOKEN_KWARG",
    "ApprovalGrant",
    "ApprovalStatus",
    "ApprovalValidationResult",
    "InMemoryApprovalStore",
]
