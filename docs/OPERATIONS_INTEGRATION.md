# Yasin-Operations Integration

This document describes how Yasin-MCP exposes a safe, read-only MCP
interface over Yasin-Operations.

## Architecture

```
MCP client (e.g. Hermes)
        |
        v
Yasin-MCP OperationsToolset (tools/operations.py)
        |
        v
OperationsAdapter (adapters/operations.py)
        |
        v  subprocess: `yasin-operations gateway`, JSONL over stdin/stdout
        v
Yasin-Operations JSONL gateway (yasin_operations/gateway.py)
        |
        v
Yasin-Operations Hermes adapter -> Core Executor
```

Yasin-MCP never imports the `yasin_operations` Python package
directly. The only integration point is spawning the
`yasin-operations` console script as a subprocess and communicating
over its `gateway` subcommand's line-delimited JSON protocol on
stdin/stdout. This keeps Yasin-MCP's own import graph completely
independent of Yasin-Operations: `import yasin_mcp` succeeds whether
or not Yasin-Operations is installed.

## Exposed MCP tools

| MCP Tool | Operations Operation | Safety |
|---|---|---|
| `yasin_operations_list_services` | `list_services` | `read_only` |
| `yasin_operations_service_status` | `service_status` | `read_only` |
| `yasin_operations_health` | `health_check` | `read_only` |
| `yasin_operations_diagnostics` | `diagnostics` | `read_only` |

This mapping is the literal `TOOL_MAP` constant in
`src/yasin_mcp/tools/operations.py`. It is not dynamic: there is no
code path anywhere in this integration that accepts a caller-
supplied operation name. Each of the four `OperationsToolset`
methods (`list_services()`, `service_status(name)`, `health()`,
`diagnostics()`) calls exactly one hardcoded `OperationsAdapter`
method, which in turn calls `_invoke()` with a hardcoded operation
constant.

## Safety boundary

Mutating Operations (`service_start`, `service_stop`,
`service_restart`, and any other non-read-only operation) are never
exposed through MCP. This is enforced at three independent layers:

1. **No code path exists.** `OperationsToolset` has no method that
   accepts an arbitrary operation name -- there is no `call()`,
   `invoke()`, or `execute()` method. `test_toolset_has_no_generic_invoke_method`
   asserts this structurally.
2. **The adapter's request builder rejects anything outside the
   four allowed operations.** `_build_request()` in
   `adapters/operations.py` raises `ValidationError` for any
   operation name not in its fixed allow-set, even though in
   practice it is only ever called with one of the four hardcoded
   constants from this module's own call sites.
3. **`safety_class` is always hardcoded to `"read_only"`** in the
   request this adapter sends -- it is never accepted as a
   parameter from any caller. A caller cannot override it.

On the Yasin-Operations side, the gateway's `Executor` independently
verifies that a request's declared `safety_class` matches the
safety class the target Tool's capability actually declares for
that operation, and rejects the request with a `VALIDATION_ERROR` on
mismatch. This is a second, independent check on the Yasin-
Operations side of the boundary -- Yasin-MCP does not rely on it as
its only line of defense, since Yasin-MCP's own hardcoded operation
set already prevents a mutating operation from ever being requested.

## Availability behavior

`OperationsAdapter.available` is a cheap, non-blocking check
(`shutil.which("yasin-operations")`) that never spawns a subprocess.
Operations tools are registered into the capability registry (via
`register_operations_tools()` in
`capabilities/operations_registration.py`) **only** when this check
passes. When Yasin-Operations is not installed, not on `PATH`, or
otherwise unavailable:

- Yasin-MCP still starts normally.
- No Operations capability is advertised at all.
- Every other MCP tool/resource continues to work unaffected.

If a call is attempted after registration but the gateway becomes
unreachable at invocation time (process disappeared, binary
removed, etc), the adapter raises `UnavailableDependencyError`
rather than crashing the server or the calling request.

## Failure handling

All failure modes become structured `McpError` subclasses, never a
raw/unhandled exception:

| Condition | Error raised |
|---|---|
| Gateway executable not on `PATH` | `UnavailableDependencyError` |
| Subprocess fails to start (`FileNotFoundError`) | `UnavailableDependencyError` |
| Gateway does not respond within the timeout | `TimeoutMcpError` |
| Gateway response exceeds the size limit | `InternalError` |
| Gateway produced no output | `InternalError` |
| Gateway output is not valid JSON | `InternalError` |
| Gateway output is valid JSON but not an object | `InternalError` |
| Empty/invalid `service_name` for `service_status` | `ValidationError` |

A structured failure result from the gateway itself (e.g. "service
not found") is not raised as an exception -- it is returned as a
normal `OperationsResult` with `success=False` and a populated
`error` field, since that is expected, structured domain output, not
an adapter-level failure.

## Evidence metadata

Every `OperationsResult` (and the dict returned by each
`OperationsToolset` method) includes:

- `source` — a string identifying the transport (`"yasin-operations
  gateway (<executable>)"`)
- `evidence_status` — `"confirmed"` when the gateway reported
  `service_available: true`, `"unresolved"` when it reported
  `service_available: false`

Neither field, nor any other field in the response, ever contains a
credential or secret -- the gateway protocol itself has no
credential-bearing fields in its request or response envelope, and
Yasin-MCP does not add any.

## Hermes integration

Documented, expected configuration (not independently live-tested
in this environment -- see Limitations below):

```bash
hermes mcp add yasin-mcp -- yasin-mcp
hermes mcp list
hermes mcp test yasin-mcp
```

For Operations capabilities specifically to be available through
this path, both the `yasin-mcp` and `yasin-operations` executables
must be installed and on `PATH` in the environment Hermes launches
`yasin-mcp` in.

## Limitations

- **No hard dependency.** `yasin_operations` is never imported by
  Yasin-MCP; the pyproject.toml dependency list is unchanged by this
  integration.
- **Live Hermes -> Yasin-MCP -> gateway -> Executor testing was not
  performed.** This sandbox environment has no Hermes installation,
  no network access to install one, and no long-running
  Yasin-Operations instance with real managed services. Faking that
  result was explicitly out of scope. Instead, `tests/test_operations_integration.py`
  exercises the *real* subprocess transport (a genuine `subprocess.run`
  call, real stdin/stdout communication) against a small fake
  gateway script that implements the exact wire protocol shape
  Yasin-Operations' `JsonlGateway` uses. This proves the transport
  and parsing logic end-to-end; it is not a substitute for testing
  against the real `yasin-operations gateway` process, and is not
  presented as one.
- **One subprocess spawn per call.** Each `OperationsAdapter` method
  call spawns a fresh `yasin-operations gateway` subprocess rather
  than reusing a long-lived process. This keeps the adapter simple
  and avoids separate subprocess lifecycle/health management, at the
  cost of per-call process-spawn latency. Acceptable for a
  diagnostics/inspection interface; would need reconsidering for a
  high-frequency use case.
- **Response size limit is a blunt instrument.** `max_response_bytes`
  (default 1MB) truncates by rejecting the whole response rather
  than streaming/paginating a large result. No Operations response
  in the current four-tool contract is expected to approach this
  size.

## Test status

225 tests pass (`pytest -q`, 0 failed, 0 skipped) as of this
integration, including 65 tests specific to the Operations
integration across `test_operations_adapter.py`,
`test_operations_tools.py`, `test_operations_registration.py`, and
`test_operations_integration.py`. See the PR description for the
full breakdown and for three pre-existing test failures found and
fixed as part of this work (one real bug in `ServerRuntime.create()`,
two incorrect test expectations unrelated to this integration).
