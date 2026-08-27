# Stage 8 — Mandatory Authentication Enforcement

## Lifecycle

```text
MCP tools/call
    → GovernanceGate.wrap_tool / execute
    → extract _yasin_auth_token (stripped from tool kwargs)
    → resolve_authentication (Stage 7.1 pipeline)
    → bind_context (fail closed on mismatch / require_auth)
    → policy evaluation
    → ALLOW → tool fn  |  DENY / APPROVAL_REQUIRED → no execution
```

## Modes

| Mode | Config | Behavior |
|------|--------|----------|
| Compatibility | `require_authentication=false` (default) | ASSERTED context; tools run under governance only |
| Required | `require_authentication=true` + `YASIN_MCP_AUTH_TOKEN` | Missing/invalid credential → `UnauthenticatedError`; no tool execution |

## Trust

- Caller cannot forge TRUSTED.
- Successful shared-secret → TRUSTED subject from **server config** (`auth_subject_id`).
- Authentication **does not** authorize tools; GovernanceGate remains authoritative.

## Credential presentation

1. Tool kwarg `_yasin_auth_token` (stripped before tool body)
2. Request scope: `auth_request_scope(presented_secret=...)`

Stdio still does **not** provide remote peer identity (Stage 7.1).

## Error bridge

SDK may still map application errors to generic tool errors. No secret leakage. Full structured bridge deferred.

## Operations

All tools including operations are registered only via `gate.wrap_tool` → same auth + governance path.
