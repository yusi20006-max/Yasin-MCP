"""Command-line entry point for Yasin-MCP."""

from __future__ import annotations

from yasin_mcp.audit.logging_setup import configure_logging
from yasin_mcp.config.config import load_config
from yasin_mcp.server.runtime import ServerRuntime


def main() -> None:
    """Load safe configuration and run the read-only stdio server."""
    config = load_config()
    configure_logging(config.log_level)
    ServerRuntime.create(config).run_stdio()
