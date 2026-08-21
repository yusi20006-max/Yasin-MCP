# Yasin-Operations Public Read-Only Integration

**Status:** CONFIRMED (Issue #41 hardening).

## Boundary

```
MCP Client → yasin_operations_* tools → OperationsAdapter → subprocess
  [yasin-operations gateway]  (JSONL stdin/stdout)
```

- No `shell=True`, no `os.system`, no eval/exec
- Command is fixed: `[executable, "gateway"]`
- Allowed operations only: `list_services`, `service_status`, `health_check`, `diagnostics`
- `safety_class` is always `read_only` (never from caller)

## Graceful degradation

| Condition | Behavior |
|-----------|----------|
| Executable not on PATH | Tools **not registered**; runtime stays healthy |
| Gateway timeout / crash | `TimeoutMcpError` / `UnavailableDependencyError` |
| `service_available=false` | `evidence_status=unresolved` |

## Evidence

- Successful gateway response with `service_available=true` → **CONFIRMED**
- Gateway present but service unavailable → **UNRESOLVED**
- Gateway absent → tools omitted (non-blocking)

## Non-goals

No command execution, lifecycle mutation, or duplication of Yasin-Operations business logic.

## Availability discovery (P2-9)

Clients can learn whether Operations tools are registered without
calling any tool:

```python
runtime = ServerRuntime.create()
info = runtime.surface_info()
# info["operations_available"] is True iff yasin-operations is on PATH
# and the four yasin_operations_* tools were registered.
```

| Signal | Meaning |
|--------|---------|
| `surface_info()["operations_available"] == True` | Gateway executable found; tools registered |
| `surface_info()["operations_available"] == False` | Not on PATH; tools omitted; runtime healthy |
| `list_tools` without `yasin_operations_*` | Same as above (discovery via catalog) |

Discovery never elevates trust and never launches the gateway; it is
a PATH check only (`shutil.which`).
