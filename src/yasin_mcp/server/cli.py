"""Command-line entry point for Yasin-MCP."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

import argparse

from yasin_mcp.audit.logging_setup import configure_logging
from yasin_mcp.config.config import load_config
from yasin_mcp.server.runtime import ServerRuntime


_PACKAGE_NAME = "yasin-mcp"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yasin-mcp",
        description="Run the read-only Yasin-MCP server over stdio.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=_package_version(),
    )
    return parser


def _package_version() -> str:
    try:
        return f"yasin-mcp {version(_PACKAGE_NAME)}"
    except PackageNotFoundError:
        return "yasin-mcp unknown"


def main() -> None:
    """Parse CLI flags, then load safe configuration and run the stdio server."""
    _build_parser().parse_args()

    config = load_config()
    configure_logging(config.log_level)
    ServerRuntime.create(config).run_stdio()
