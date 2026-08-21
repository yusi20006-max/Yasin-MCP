# Audit — P0 Phase A3: MCP Runtime and Real Client Compatibility Audit

**Date:** this audit  
**Scope:** Issue #37. Evidence-based only; no invented contracts. Live protocol verification only — unit/integration/mocked paths are explicitly separated and not counted as live compatibility evidence.

## Evidence classification

Same as `docs/AUDIT_P0_A1.md` / `docs/AUDIT_P0_A2.md`:

- **CONFIRMED** — directly observed from live execution, repository code, or a passing automated check.
- **TARGET** — documented intent, not verified as implemented in the observed path.
- **PROPOSED** — a suggestion, not implemented.
- **UNRESOLVED** — could not be determined from available evidence.

## 1. Scope

Verify that the actual Yasin-MCP runtime works with a real MCP client over the production stdio transport, not only unit or mocked paths.

In scope:

- Server startup via the real CLI entrypoint (`yasin-mcp` / `yasin_mcp.server.cli:main`)
- stdio transport
- MCP initialize handshake
- protocol/version negotiation
- server capabilities advertisement
- `list_tools`
- tool metadata (when tools present)
- `call_tool` for an allowed read-only tool (structure; domain tools conditional)
- returned result structure
- error behavior for an invalid/non-existent tool
- graceful shutdown

Out of scope for this issue: implementing new domain tools, changing Operations registration policy, P1 roadmap work.

## 2. Environment

| Item | Value |
|------|--------|
| Host | Linux (sandbox) |
| Python | 3.12.3 |
| Project venv | `/tmp/yasinmcp_venv` |
| Package | `yasin-mcp==0.1.0` (editable install from this repository) |
| MCP SDK | `mcp==2.0.0` (dependency declared `mcp>=2,<3`) |
| Client used | Official `mcp.client.stdio.stdio_client` + `mcp.ClientSession` |
| Server entrypoint | `/tmp/yasinmcp_venv/bin/yasin-mcp` (console script → `yasin_mcp.server.cli:main`) |
| Operations gateway | **Not on PATH** → `OperationsAdapter.available == False` → zero Operations tools registered (expected) |
| Working tree at test | `main` @ `2f0f700` (P0 A2 merge) plus this audit’s documentation-only commit |

## 3. Exact runtime/client test methodology

1. Install the package into a clean venv:  
   `python3 -m venv /tmp/yasinmcp_venv && pip install -e ".[dev]"`
2. Spawn the **real** CLI as a subprocess over stdio using the official client:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

params = StdioServerParameters(
    command="/tmp/yasinmcp_venv/bin/yasin-mcp",
    args=[],
    cwd="<repo root>",
    env={"PATH": "/tmp/yasinmcp_venv/bin:/usr/bin:/bin"},
)
async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        init_result = await session.initialize()
        tools = await session.list_tools()
        err = await session.call_tool("nonexistent_xyz", {})
# context managers exit → graceful shutdown
```

3. No mocks of `MCPServer`, no patched `run_stdio`, no in-process-only path counted as the primary live evidence.  
   A supplemental in-process `Client(server)` run was used only to observe successful `call_tool` result shape when a temporary tool is registered; that path is labeled supplemental and is **not** the live stdio evidence.

## 4. Evidence collected

### Evidence class labels (required by Issue #37)

| Label | Source | Counts as live compatibility? |
|-------|--------|-------------------------------|
| **UNIT_TEST** | `tests/test_runtime.py`, `tests/test_protocol_contracts.py`, etc. | **No** |
| **INTEGRATION_TEST** | `tests/test_operations_runtime.py`, `tests/test_operations_registration.py` | **No** |
| **LIVE_RUNTIME** | Subprocess `yasin-mcp` over stdio, this audit’s client script | **Yes** |
| **REAL_MCP_CLIENT** | `mcp==2.0.0` `stdio_client` + `ClientSession` | **Yes** |

Mocked or unit-test evidence is **not** classified as live compatibility evidence.

### 4.1 Initialize result — CONFIRMED (LIVE_RUNTIME / REAL_MCP_CLIENT)

```
protocol_version: 2025-11-25
server_info: name='Yasin-MCP' version='0.1.0'
  description='AI/Agent-facing access layer for the Yasin ecosystem'
capabilities: experimental={} logging=None
  prompts=PromptsCapability(list_changed=False)
  resources=ResourcesCapability(subscribe=False, list_changed=False)
  tools=ToolsCapability(list_changed=False)
  completions=None extensions=None tasks=None
instructions: None
```

Handshake completed without error. Server identity matches `ServerRuntime` / `MCPServer` construction.

### 4.2 Protocol / version negotiation — CONFIRMED

Negotiated protocol version on the live stdio path: **`2025-11-25`**.  
Session attributes after initialize: `session.protocol_version == "2025-11-25"`, `session.server_info` matches initialize result.

Note: an in-process `Client(MCPServer)` path (supplemental) negotiated `2026-07-28`. Both are valid outcomes of the same server binary under different client connection modes; the production transport under test is stdio, which negotiated `2025-11-25`.

### 4.3 Server capabilities — CONFIRMED

Live stdio capabilities (see 4.1): tools/prompts/resources list_changed flags are `False` on this path; experimental and other optional capabilities empty/None. Tools capability is present (server advertises tools support) even when the tool list is empty.

### 4.4 list_tools result — CONFIRMED

```
tools count: 0
tools: []
result_type: complete
meta: None
```

**Expected** when `yasin-operations` is not on PATH: `register_operations_tools` returns `False` and no `server.add_tool` calls occur. Empty list is a valid MCP response, not a protocol failure.

### 4.5 Tool metadata — CONFIRMED (empty set)

No tool descriptors returned. When Operations tools *are* registered (gateway available), metadata would include names `yasin_operations_list_services`, `yasin_operations_service_status`, `yasin_operations_health`, `yasin_operations_diagnostics` with structured_output schemas — verified by unit/integration tests and by code inspection of `server/runtime.py`, but **not** by this live run (gateway absent).

Supplemental (in-process temporary tool only): `input_schema` auto-derived from function signature; description taken from docstring. Not production code.

### 4.6 call_tool for an allowed read-only tool — CONFIRMED structure (conditional availability)

Live stdio path: **no domain tools registered** → no successful domain `call_tool` possible without the Operations gateway. This is the correct production behavior when the gateway is missing (server still starts; other future capabilities would be unaffected).

Supplemental structure observation (temporary tool, in-process only, **not** counted as live domain compatibility):

```
call is_error: False
call content: [TextContent(type='text', text='{\n  "echo": "live-ok",\n  "evidence_status": "CONFIRMED"\n}', ...)]
call structured_content: {'echo': 'live-ok', 'evidence_status': 'CONFIRMED'}
call result_type: complete
```

### 4.7 Returned result structure — CONFIRMED

Invalid-tool and supplemental successful paths both return objects with:

- `is_error: bool`
- `content: list[TextContent | ...]`
- `structured_content: dict | None`
- `result_type: "complete"` (observed)
- `meta: None | dict`

### 4.8 Error behavior for invalid / non-existent tool — CONFIRMED

```
is_error: True
content: [TextContent(type='text', text='Unknown tool: nonexistent_xyz', annotations=None, meta=None)]
structured_content: None
result_type: complete
```

No crash, no hang, structured error flag set. Protocol continues to accept further messages until session close.

### 4.9 Graceful shutdown — CONFIRMED

Exiting the `stdio_client` / `ClientSession` async context managers caused the server subprocess to terminate cleanly. No hang observed; outer script reached `SHUTDOWN COMPLETE`.

## 5. Client compatibility result — CONFIRMED

| Check | Result |
|-------|--------|
| Official MCP Python client (`mcp==2.0.0`) can connect over stdio | Pass |
| Initialize handshake | Pass |
| Version negotiation | Pass (`2025-11-25` on stdio) |
| Capabilities readable | Pass |
| `list_tools` | Pass (empty when Operations unavailable) |
| Invalid tool error shape | Pass |
| Graceful teardown | Pass |
| Domain tool invocation without Operations gateway | N/A (correctly unavailable) |

**No protocol defect was observed.** No code change to the server was required for this audit.

## 6. Limitations

- Live domain tool success path was **not** exercised because `yasin-operations` was not installed on PATH in the audit environment. Registration logic and tool handlers remain covered by **UNIT_TEST** / **INTEGRATION_TEST** only for that path.
- Protocol version differs between stdio client path (`2025-11-25`) and in-process Client path (`2026-07-28`); both succeeded. Full multi-version matrix across all MCP clients is not claimed.
- `server/cli.py` remains at **0%** automated coverage (documented in A1); this live run exercises it once but is not a regression suite.
- Resources and prompts were not listed/read in this live run (none registered); capabilities flags only observed.

## 7. CONFIRMED / TARGET / PROPOSED / UNRESOLVED

### CONFIRMED

- Real stdio MCP server starts via CLI entrypoint and completes initialize with official client.
- Protocol negotiation, capabilities, `list_tools` (empty), invalid-tool error, and graceful shutdown work.
- Empty tool list when Operations gateway unavailable is intentional and non-fatal.
- Quality gate on the tree used for this audit: 227 pytest passed, 88% coverage, ruff check/format clean, mypy clean, bandit no high-severity issues, compileall clean.
- No live protocol defect requiring a code fix.

### TARGET

- Live verification of the four Operations tools when the gateway is present (same client methodology).
- Automated smoke test in CI that runs a short real-client stdio session (optional hardening).

### PROPOSED

- Optional always-on read-only diagnostic tool (e.g. `yasin_mcp_self_status`) so `list_tools` is non-empty even without Operations — only if product intent requires a non-empty tool list for client demos.
- Explicit CI job matrix entry for “live stdio handshake” using the same client script as this audit.

### UNRESOLVED

- Whether every third-party MCP client (non-Python, older protocol versions) negotiates successfully — only the official Python `mcp==2.0.0` client was used here.
- Exact reason for protocol version difference between stdio vs in-process Client modes (library behavior; server accepts both).

## 8. Final assessment

**Issue #37 acceptance criteria are met:**

- Real client compatibility findings are documented (this file).
- Mock-only coverage is clearly separated from live evidence (section 4 evidence table).
- No runtime blockers were found; therefore no reproduction steps for a defect and no code fix were required.
- Safe smoke-test baseline is established (section 3 methodology + section 4 results).

P0 Phase A3 complete. No production code changes. Documentation-only delivery for this issue.
