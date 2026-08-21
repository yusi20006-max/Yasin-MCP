"""Request correlation context (P2-4)."""

import logging

from yasin_mcp.audit.context import get_request_id, request_scope
from yasin_mcp.audit.logging_setup import configure_logging, log_with_context, redact
from yasin_mcp.audit.traced import run_traced


def test_request_scope_sets_and_clears_id() -> None:
    assert get_request_id() is None
    with request_scope("fixed-id") as rid:
        assert rid == "fixed-id"
        assert get_request_id() == "fixed-id"
    assert get_request_id() is None


def test_run_traced_propagates_request_id() -> None:
    seen: list[str | None] = []

    def work() -> str:
        seen.append(get_request_id())
        return "ok"

    result = run_traced("unit_test_op", work, fields={"token": "should-redact", "path": "a"})
    assert result == "ok"
    assert seen[0] is not None


def test_redact_strips_secrets() -> None:
    payload = redact({"token": "secret", "path": "docs/a.md", "nested": {"api_key": "x"}})
    assert payload["token"] == "***"
    assert payload["path"] == "docs/a.md"
    assert payload["nested"]["api_key"] == "***"


def test_log_with_context_accepts_request_id() -> None:
    logger = configure_logging()
    log_with_context(logger, logging.INFO, "correlated", request_id="rid-1", fields={"k": 1})
