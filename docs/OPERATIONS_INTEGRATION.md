# Yasin-Operations Integration

This document describes how Yasin-MCP exposes a safe, read-only MCP interface over Yasin-Operations.

## Architecture

```text
Hermes
  │
  │ MCP / stdio
  ▼
Yasin-MCP
  │
  │ OperationsAdapter / JSONL boundary
  ▼
Yasin-Operations
  │
  ▼
Executor → SafetyPolicy → ToolRegistry
```

Yasin-Operations remains the operational authority and is **not** an MCP server. Its existing JSONL gateway remains unchanged. Yasin-MCP is the MCP boundary presented to Hermes and other MCP clients.

Yasin-MCP never imports the `yasin_operations` Python package directly. The integration point is the `yasin-operations gateway` executable and its line-delimited JSON protocol over stdin/stdout. This keeps Yasin-MCP independently importable when Yasin-Operations is absent.

## Exposed MCP tools

Exactly four read-only tools are exposed when the Operations gateway is available:

| MCP Tool | Operations Operation | Safety |
|---|---|---|
| `yasin_operations_list_services` | `list_services` | `read_only` |
| `yasin_operations_service_status` | `service_status` | `read_only` |
| `yasin_operations_health` | `health_check` | `read_only` |
| `yasin_operations_diagnostics` | `diagnostics` | `read_only` |

The mapping is the literal `TOOL_MAP` constant in `src/yasin_mcp/tools/operations.py`. No caller can supply an arbitrary Operations operation name or `safety_class`.

The MCP runtime registers these exact four functions with the official MCP Python SDK. Capability registration and actual MCP tool registration use the same availability check, so a missing Operations gateway cannot result in advertised-but-unusable tools.

### Input schemas

`yasin_operations_list_services`, `yasin_operations_health`, and `yasin_operations_diagnostics` accept an empty JSON object with no additional properties.

`yasin_operations_service_status` requires exactly one field:

```json
{
  "service_name": "yasin-ai"
}
```

Unknown fields are rejected by the MCP tool schema, and empty service names are rejected by the adapter.

## Safety boundary

Mutating Operations are never exposed through MCP. This is enforced at three independent layers:

1. `OperationsToolset` contains only the four named methods. There is no generic `call()`, `invoke()`, or `execute()` method.
2. `_build_request()` rejects any operation outside the fixed four-item allow-set.
3. `safety_class` is hardcoded to `read_only` and is never accepted from a caller.

Yasin-Operations independently validates the declared safety class against its own tool capability before execution. MCP therefore does not bypass the existing Operations safety boundary.

No arbitrary shell/process execution, generic operation passthrough, lifecycle mutation, deployment, or filesystem mutation is exposed by this bridge.

## Availability behavior

`OperationsAdapter.available` uses a non-blocking executable lookup. If `yasin-operations` is unavailable:

- Yasin-MCP still starts normally.
- No Operations MCP tools are advertised.
- Other Yasin-MCP capabilities remain unaffected.

If the gateway becomes unavailable after startup, the adapter returns a structured MCP dependency error rather than exposing a raw subprocess exception.

## Hermes registration

Hermes must register **Yasin-MCP**, not Yasin-Operations directly.

From an environment where the `yasin-mcp` executable is installed:

```bash
hermes mcp add yasin-mcp -- yasin-mcp
hermes mcp list
hermes mcp test yasin-mcp
```

The expected configuration is equivalent to:

```text
server name: yasin-mcp
command:     yasin-mcp
transport:   stdio
```

For the four Operations tools to be available, `yasin-operations` must also be installed and discoverable on the same `PATH` inherited by the Hermes-launched Yasin-MCP process.

The exact Hermes CLI commands above are documented integration instructions; this repository's automated tests do not claim a live Hermes installation is available.

## End-to-end behavior

The intended runtime path is:

```text
Hermes
  │
  │ list_tools / call_tool
  ▼
Yasin-MCP MCPServer
  │
  ▼
OperationsToolset
  │
  ▼
OperationsAdapter
  │
  │ fixed argv: ["yasin-operations", "gateway"]
  │ JSONL over stdin/stdout
  ▼
Yasin-Operations Gateway
  │
  ▼
Executor / SafetyPolicy / ToolRegistry
```

The repository test suite verifies the MCP runtime registration boundary and the real subprocess transport against a deterministic fake gateway implementing the same JSONL envelope. A real Hermes process and live Yasin-Operations deployment are external integration tests and are not represented as passing evidence unless actually executed.

## Evidence metadata

Every successful or structured gateway response includes:

- `source` — identifies the Yasin-Operations gateway transport.
- `evidence_status` — `confirmed` when the gateway reports availability and `unresolved` when it does not.

Yasin-MCP does not invent service state when the upstream source is unavailable.

## Failure handling

| Condition | Result |
|---|---|
| Gateway executable unavailable | `UnavailableDependencyError` |
| Gateway cannot start | `UnavailableDependencyError` |
| Gateway timeout | `TimeoutMcpError` |
| Oversized response | `InternalError` |
| Empty/malformed response | `InternalError` |
| Invalid `service_name` | `ValidationError` |
| Normal upstream failure response | Structured `OperationsResult` with `success=false` |

Internal exception text, credentials, environment variables, and arbitrary subprocess details are not exposed to MCP callers.

## Independence

`yasin_operations` is intentionally not a Python dependency of Yasin-MCP. A clean environment without Yasin-Operations can import and start Yasin-MCP; the Operations capability simply remains unavailable.

## Validation status

Automated validation covers:

- exact four-tool registration;
- absence of Operations tools when the gateway is unavailable;
- explicit tool schemas;
- adapter allow-list and fixed safety class;
- malformed and oversized gateway responses;
- timeout and unavailable-gateway behavior;
- real subprocess JSONL transport using a deterministic fake gateway;
- security checks and secret-leakage regression tests.

A live Hermes → Yasin-MCP → Yasin-Operations → Executor test requires the Hermes runtime and a real Yasin-Operations environment and must be reported separately when performed.
