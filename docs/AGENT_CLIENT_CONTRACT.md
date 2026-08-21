# Yasin-Agent ↔ Yasin-MCP Client Integration Contract

**Version:** 1.0.0  
**Status:** CONFIRMED as a documented public contract (Issue #42).

## Constraint

Yasin-Agent **must not** gain a mandatory runtime dependency on Yasin-MCP.

## Fallback

| Condition | Behavior |
|-----------|----------|
| Binary missing | Continue without MCP tools |
| Timeout | Surface error; bounded retries only |
| Tool error | Preserve error envelope; no invented data |

See `yasin_mcp.contracts.agent_client`.
