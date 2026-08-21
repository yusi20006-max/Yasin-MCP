# Live MCP Client Regression Harness (P2-2)

**Evidence class:** `LIVE_RUNTIME`

## Purpose

Prove the real `yasin-mcp` process works with the official MCP Python SDK over
stdio after the P1 tool surface expansion (non-empty always-on catalog).

## How to run

```bash
pip install -e ".[dev]"
pytest tests/test_live_mcp_client_harness.py -q
```

Uses the `yasin-mcp` console script from the active environment.

## Checks

1. initialize
2. protocol version negotiation
3. server identity
4. capabilities
5. `list_tools` — always-on prefixes: `yasin_docs_*`, `yasin_github_*`, `yasin_registry_*`
6. `call_tool` on a docs list tool (success or structured error offline)
7. invalid tool → error/content shape
8. graceful shutdown via context exit

## CI

Default PR CI does **not** require `YASIN_MCP_GITHUB_TOKEN`. Network failures on
domain tool calls are accepted as structured results; discovery must still pass.

## Not claimed

- Live GitHub/Docs data fetch success in CI (see optional P2-7)
- Hermes / Yasin-Agent live client (P2-8)
