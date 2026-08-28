# Stage 12 — Authenticated Remote Transport

**Issue #98**

## Mechanism

HTTPS + Bearer shared-secret (`YASIN_MCP_AUTH_TOKEN`), constant-time compare.
Does not claim remote peer identity (mTLS/OIDC deferred).

## Architecture

HTTP(S) → RequireBearerAuthMiddleware → auth_request_scope → MCP streamable-HTTP → GovernanceGate → tools

## Config

`YASIN_MCP_REMOTE_*`, TLS required unless `REMOTE_ALLOW_INSECURE_HTTP` for local tests.
CLI: `yasin-mcp --transport remote`

## Trust

ASSERTED context fields; TRUSTED only via shared-secret → configured subject.

## Non-goals

OAuth platform, mTLS infra, Hub/Control Plane, Stages 13–15.
