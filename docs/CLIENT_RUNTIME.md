# Client Runtime Guide (P2-7 / P2-8)

**Status:** CONFIRMED for stdio MCP clients. External agents (Hermes,
generic Agent hosts) use the same contract — no proprietary dependency.

## Quick start (stdio)

```bash
# from a checkout with the package installed
python -m yasin_mcp
# or: yasin-mcp  (console script if installed)
```

### Example MCP client config (generic)

```json
{
  "mcpServers": {
    "yasin-mcp": {
      "command": "python",
      "args": ["-m", "yasin_mcp"],
      "env": {}
    }
  }
}
```

Optional env:

| Variable | Purpose |
|----------|---------|
| `GITHUB_TOKEN` / config token | Higher GitHub rate limits (read-only) |
| PATH containing `yasin-operations` | Registers optional ops tools |

## Smoke checklist

1. **Process starts** and speaks MCP over stdio.
2. **`initialize`** succeeds; server name `Yasin-MCP`.
3. **`list_tools`** returns a **non-empty** catalog (docs + github + registry always; operations only if gateway on PATH).
4. **`call_tool`** on a safe tool (e.g. surface/docs list) returns structured payload with evidence/provenance.
5. **Error path**: invalid args → structured MCP error, process stays up.
6. **Shutdown** clean.

Automated coverage: `tests/test_live_mcp_client_harness.py` (mark `LIVE_RUNTIME`).
See also `docs/LIVE_MCP_HARNESS.md`.

## External clients (Hermes / Agent)

Yasin-MCP does **not** depend on Hermes or any specific agent SDK.
Any MCP-compatible stdio client is valid. Validation evidence is the
live harness above, not a vendor-specific integration package.

## Capability surface

```python
from yasin_mcp.server.runtime import ServerRuntime

info = ServerRuntime.create().surface_info()
# capability_surface_version, operations_available, always_on_prefixes, ...
```

## Non-goals

- No mandatory third-party agent package
- No mutating tools
- No shell execution
