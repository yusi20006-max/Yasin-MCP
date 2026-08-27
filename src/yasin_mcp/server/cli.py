"""Command-line entry point for Yasin-MCP."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version

from yasin_mcp.audit.logging_setup import configure_logging
from yasin_mcp.config.config import InvalidConfigurationError, load_config
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
    """Parse CLI flags, then load safe configuration and run the stdio server.

    Invalid configuration fails deterministically with a non-zero exit code
    and a secret-free message (Issue #84).
    """
    _build_parser().parse_args()

    try:
        config = load_config()
    except InvalidConfigurationError as exc:
        # Message is validation text only — never includes secret values.
        print(f"yasin-mcp: configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    configure_logging(config.log_level)
    ServerRuntime.create(config).run_stdio()
