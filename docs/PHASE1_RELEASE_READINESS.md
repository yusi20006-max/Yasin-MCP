# Yasin-MCP Phase 1 Release Readiness

## Status

Phase 1 is a **read-only release candidate**. Phase 2 is not part of this release.

## Implemented Surface

| Area | Status | Evidence |
|---|---|---|
| MCP protocol contracts | Implemented | `protocol/` |
| Capability discovery | Implemented | `capabilities/registry.py` |
| Security/policy boundary | Implemented | `policies/` |
| Structured logging/redaction | Implemented | `audit/logging_setup.py` |
| MCP runtime | Implemented | `server/runtime.py` |
| stdio transport | Implemented | `ServerRuntime.run_stdio()` |
| YASIN-DOCS adapter | Implemented | `adapters/docs.py` |
| GitHub adapter | Implemented | `adapters/github.py` |
| Project registry adapter | Implemented | `adapters/project_registry.py` |
| Diagnostics/health boundary | Implemented | `diagnostics/health.py` |
| Phase 1 security matrix | Implemented | `tests/test_phase1_matrix.py` |

## Evidence Semantics

- `CONFIRMED`: observed directly from an authoritative source or implementation.
- `TARGET`: documented intent that has not been verified as runtime behavior.
- `PROPOSED`: planned capability not implemented.
- `UNRESOLVED`: the available sources did not establish the fact.

Yasin-MCP must never convert a target architecture document into a claim of runtime implementation.

## Client Configuration

The server is currently intended for local stdio clients. A client should launch the installed executable:

```text
yasin-mcp
```

No credentials are embedded in client configuration. GitHub access is optional and is supplied through the environment variable:

```text
YASIN_MCP_GITHUB_TOKEN
```

The token is wrapped by `SecretStr` and must never be returned by tools or logs.

## Supported Runtime

- Python 3.10+
- Official MCP Python SDK v2 (`mcp>=2,<3`)
- Phase 1 default transport: stdio

## Optional Integrations

Yasin-Operations is optional. When it is absent, diagnostics return `UNRESOLVED` rather than inventing a health state.

YASIN-DOCS is read through a fixed, bounded adapter. GitHub is accessed only through explicit read-only adapter methods.

## Read-Only Gate

Phase 1 does not expose:

- arbitrary shell/process execution;
- filesystem mutation;
- GitHub writes;
- deployment;
- start/stop/restart;
- memory mutation;
- arbitrary API passthrough.

Future mutation safety classes remain denied while `PHASE_1_READ_ONLY` is enabled.

## Release Checklist

- [x] Repository baseline exists.
- [x] Protocol contracts exist.
- [x] Security policy exists.
- [x] MCP runtime exists.
- [x] YASIN-DOCS adapter exists.
- [x] GitHub read adapter exists.
- [x] Project registry adapter exists.
- [x] Diagnostics boundary exists.
- [x] Phase 1 security/integration matrix exists.
- [ ] Final CI run is green on the release candidate commit.
- [ ] Final manual client smoke test completed in a real MCP host.

The final two items are release-gate evidence requirements and must not be claimed as complete without actual CI/client evidence.

## Phase 2 Prerequisites

Before enabling Phase 2 integrations:

1. YASIN-DOCS should formally record Yasin-MCP in its canonical architecture/project registry.
2. Public contracts for Yasin-Core, Yasin-Agent, Yasin-AI, YasinHub, and Yasin-Operations should be identified and versioned where needed.
3. Any mutation capability requires a separate authorization and safety decision.
4. Remote HTTP transport requires explicit authentication and transport-security design.
