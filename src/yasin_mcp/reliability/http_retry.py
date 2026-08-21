"""Bounded HTTP GET with rate-limit retries for idempotent reads."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from yasin_mcp.audit.context import get_request_id
from yasin_mcp.audit.logging_setup import configure_logging, log_with_context
from yasin_mcp.errors.errors import (
    NotFoundError,
    RateLimitedError,
    TimeoutMcpError,
    UnauthenticatedError,
    UnavailableDependencyError,
    UpstreamError,
)
from yasin_mcp.reliability.policy import default_policy


def github_get_json(
    url: str,
    headers: dict[str, str],
    timeout: int,
    *,
    max_response_bytes: int,
) -> Any:
    """GET JSON with bounded rate-limit retries. No timeout retries."""
    policy = default_policy()
    logger = configure_logging()
    attempt = 0
    while True:
        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=timeout) as response:  # nosec B310
                raw = response.read(max_response_bytes + 1)
        except HTTPError as exc:
            if exc.code == 401:
                raise UnauthenticatedError("GitHub authentication failed") from exc
            if exc.code == 404:
                raise NotFoundError("GitHub resource was not found") from exc
            if exc.code in (403, 429):
                if policy.should_retry(error_kind="rate_limit", attempt=attempt):
                    delay = policy.delay_for_attempt(attempt)
                    log_with_context(
                        logger,
                        20,
                        "retry:github_rate_limit",
                        request_id=get_request_id(),
                        fields={"attempt": attempt, "delay": delay, "status": exc.code},
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue
                raise RateLimitedError(
                    "GitHub denied the request or rate limit was reached"
                ) from exc
            raise UpstreamError(f"GitHub returned HTTP {exc.code}") from exc
        except TimeoutError as exc:
            raise TimeoutMcpError("GitHub request timed out") from exc
        except URLError as exc:
            raise UnavailableDependencyError("GitHub is unavailable") from exc
        if len(raw) > max_response_bytes:
            raise UpstreamError("GitHub response exceeded the configured size limit")
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UpstreamError("GitHub returned invalid JSON") from exc
