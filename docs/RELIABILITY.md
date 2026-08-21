# Reliability Policy (P2-5)

**Status:** CONFIRMED

## Timeouts

- Configured via `ServerConfig.request_timeout_seconds` (1–120, default 30).
- Adapter HTTP and Operations gateway calls honor this timeout.
- Timeout errors are deterministic and are **not** retried by default.

## Bounded retries

| Parameter | Value |
|-----------|-------|
| Max safe retries | 2 |
| Backoff | deterministic: 0.05s, 0.15s |
| Retry on rate-limit (403/429) | yes (GitHub read path) |
| Retry on timeout | no |
| Unbounded loops | none |

Retries apply only to **idempotent read** operations. Mutation tools do not exist on this surface.

## Rate limits

After the retry budget is exhausted, `RateLimitedError` is raised as a structured MCP error. Clients must treat rate-limit as explicit failure, not silent success.

## Caching

No aggressive cache is introduced for convenience.
