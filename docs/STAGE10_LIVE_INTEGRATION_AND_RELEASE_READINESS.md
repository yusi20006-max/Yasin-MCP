# Stage 10 — Live MCP Integration Validation & Controlled Release Readiness

**Issue #94**

## Evidence classes

| Class | Meaning |
|-------|---------|
| **LIVE** | Real `yasin-mcp` subprocess + MCP Python client over stdio |
| **INTEGRATION** | `GovernanceGate.wrap_tool` / `execute` |
| **STATIC** | Source/path inspection |

## LIVE verified

- Startup / initialize / tools/list
- Compat mode READ_ONLY path (or structured upstream failure)
- Unknown tool → isError (SDK manager for unregistered names)
- require_auth + missing present → AUTHENTICATION_REQUIRED JSON ToolError
- Invalid present → auth failure, secret-free
- Valid present → not auth-blocked
- Sequential sessions isolation; clean shutdown

## Credential presentation (stdio)

| Mechanism | Class |
|-----------|--------|
| `_yasin_auth_token` kwarg | CONFIRMED (stripped) |
| contextvar scope | CONFIRMED |
| `YASIN_MCP_PRESENT_AUTH_TOKEN` env | CONFIRMED process-boundary |

stdio peer principal remains **UNRESOLVED**.

## DENY / APPROVAL on live catalog

Production tools are READ_ONLY. DENY/APPROVAL codes are **INTEGRATION**-verified via wrap_tool (Stages 8–9).

## Controlled integration readiness

**READY WITH NOTES** — no remote HTTPS/OAuth/mTLS; upstream GitHub may rate-limit.
