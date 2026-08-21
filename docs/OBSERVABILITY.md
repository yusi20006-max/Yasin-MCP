# Observability and Request Correlation (P2-4)

**Status:** CONFIRMED

## Request correlation

- `yasin_mcp.audit.context.request_scope` / `get_request_id`
- `new_request_id()` generates UUID correlation IDs
- Operations gateway requests reuse the active request ID when present

## Structured logging

- JSON single-line logs via `JsonFormatter`
- `log_with_context(..., request_id=..., fields=...)`
- `run_traced(operation, fn, fields=...)` wraps external I/O with start/error/end events

## Redaction

Sensitive keys (`token`, `secret`, `password`, `authorization`, `api_key`, …) are recursively replaced with `***` before logging. Raw secret values must not appear in log payloads.

## Path demonstrated

MCP tool invocation → adapter external call → `request_id` on Operations envelope / structured log fields → response or structured error.
