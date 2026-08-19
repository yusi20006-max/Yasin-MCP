import json
import logging

from yasin_mcp.audit.logging_setup import (
    JsonFormatter,
    configure_logging,
    log_with_context,
    new_request_id,
)


def test_new_request_id_is_unique():
    a = new_request_id()
    b = new_request_id()
    assert a != b


def test_new_request_id_is_nonempty_string():
    rid = new_request_id()
    assert isinstance(rid, str)
    assert len(rid) > 0


def test_json_formatter_produces_valid_json():
    record = logging.LogRecord(
        name="yasin_mcp.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    formatter = JsonFormatter()
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["message"] == "hello"
    assert parsed["level"] == "INFO"


def test_json_formatter_includes_request_id_when_present():
    record = logging.LogRecord(
        name="yasin_mcp.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.request_id = "abc-123"
    formatter = JsonFormatter()
    parsed = json.loads(formatter.format(record))
    assert parsed["request_id"] == "abc-123"


def test_json_formatter_omits_request_id_when_absent():
    record = logging.LogRecord(
        name="yasin_mcp.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    formatter = JsonFormatter()
    parsed = json.loads(formatter.format(record))
    assert "request_id" not in parsed


def test_configure_logging_returns_logger():
    logger = configure_logging()
    assert logger.name == "yasin_mcp"


def test_configure_logging_idempotent_handler_setup():
    logger1 = configure_logging()
    handler_count_1 = len(logger1.handlers)
    logger2 = configure_logging()
    handler_count_2 = len(logger2.handlers)
    assert handler_count_1 == handler_count_2


def test_log_with_context_does_not_raise():
    logger = configure_logging()
    # Should not raise regardless of request_id/fields being None
    log_with_context(logger, logging.INFO, "test message")
    log_with_context(logger, logging.INFO, "test message", request_id="abc", fields={"k": "v"})
