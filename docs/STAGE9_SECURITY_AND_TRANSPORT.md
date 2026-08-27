# Stage 9 — Authenticated Transport, Structured MCP Errors & Integration Security

**Issue #92**

## Structured MCP error contract (IMPLEMENTED)

Application `McpError` subclasses raised from governed tools are converted in
`GovernanceGate.wrap_tool` to MCP SDK **`ToolError`** with a JSON message containing
`code`, `category`, `message`, and safe `details`.

Uses the supported SDK path: anticipated `ToolError` → `isError=True` (not crash mapping).

## Credential transport (IMPLEMENTED abstraction)

| Item | Classification |
|------|----------------|
| `_yasin_auth_token` stdio kwarg | CONFIRMED |
| Credential reaches tool body | CONFIRMED prevented |
| Stdio remote peer identity | UNRESOLVED / unavailable |

## Remote authenticated transport (ARCHITECTURE ONLY)

HTTPS / OAuth / mTLS = TARGET. **Not implemented** in Stage 9.

## Replay

Request isolation CONFIRMED; cryptographic replay protection UNRESOLVED / TRANSPORT-DEPENDENT.

## Explicit non-goals

Agent, Hub, Control Plane, OAuth platform, mTLS infra, PyPI, Stage 10.
