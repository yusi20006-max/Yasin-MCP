"""Stage 8 — mandatory authentication before governance execution."""

from __future__ import annotations

from typing import Any

from yasin_mcp.auth.binding import BoundRequestContext
from yasin_mcp.auth.pipeline import resolve_authentication
from yasin_mcp.auth.request_state import (
    AUTH_TOKEN_KWARG,
    get_asserted_context,
    get_presented_secret,
)
from yasin_mcp.config.config import ServerConfig
from yasin_mcp.contracts.integration_context import IntegrationContext
from yasin_mcp.governance.types import GovernanceContext


def extract_presented_secret(kwargs: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """Remove reserved auth kwarg from tool kwargs; never leave it for the tool."""
    cleaned = dict(kwargs)
    presented = cleaned.pop(AUTH_TOKEN_KWARG, None)
    if presented is not None and not isinstance(presented, str):
        presented = str(presented)
    if presented is None:
        presented = get_presented_secret()
    return cleaned, presented


def resolve_execution_auth(
    config: ServerConfig | None,
    *,
    context: GovernanceContext | None = None,
    presented_secret: str | None = None,
    asserted: IntegrationContext | None = None,
) -> BoundRequestContext | None:
    """Resolve auth when a security config is attached.

    Returns None when no security config is configured (tests constructing
    GovernanceGate without ServerConfig). When config is present, always
    runs the Stage 7.1 pipeline (compatibility mode or require_auth).
    """
    if config is None:
        return None

    if asserted is None:
        asserted = get_asserted_context()
    if asserted is None and context is not None:
        asserted = IntegrationContext(
            client_id=context.client_id,
            agent_id=context.agent_id,
            project_id=context.project_id,
            workspace_id=context.workspace_id,
            task_id=context.task_id,
            session_id=context.session_id,
            request_id=context.request_id,
            correlation_id=context.correlation_id,
            extra=dict(context.extra) if context.extra else None,
        )
    if presented_secret is None:
        presented_secret = get_presented_secret()

    return resolve_authentication(
        config=config,
        asserted=asserted,
        presented_secret=presented_secret,
    )
