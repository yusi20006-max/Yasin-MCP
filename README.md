# Yasin-MCP

Standalone AI/Agent-facing MCP (Model Context Protocol) access and integration layer for the Yasin ecosystem.

## Status

**Yasin-MCP roadmap Stages 1–15 are complete on the controlled-integration path.** Master #96 is the roadmap closure gate. After Stage 15 merges with its final quality evidence, no planned Stage 16 remains.

The repository is **READY_FOR_CONTROLLED_RELEASE / READY_FOR_CONTROLLED_INTEGRATION**. This classification does not claim a production deployment or package publication that has not actually occurred.

### Roadmap completion evidence

- **Stage 11 / #97:** merged.
- **Stage 12 / #98 → PR #103:** merged.
- **Stage 13 / #99 → PR #104:** merged; live ecosystem-compatible MCP client path verified over authenticated Streamable HTTP, including identity propagation, governance, approval, execution, audit correlation, and fail-closed malformed context handling.
- **Stage 14 / #100 → PR #105 and lifecycle-resilience PR #106:** merged; bounded concurrency, deterministic lifecycle/isolation coverage, stress behavior, cleanup, slot recovery, and post-stress usability are covered.
- **Stage 15 / #101:** final release, reproducibility, compatibility, documentation, transport, security, and roadmap-closure verification.

See [`docs/RELEASE_READINESS.md`](docs/RELEASE_READINESS.md) for the current final assessment.

## Architecture boundary

Yasin-MCP does **not** replace YASIN-DOCS, Yasin-Core, Yasin-Agent, Yasin-AI, YasinHub, YasinCLI, or Yasin-Operations. It is an access/integration layer.

- MCP capabilities are read-only at the product surface unless an explicitly governed reference capability is present for testing governance behavior.
- No generic shell passthrough or arbitrary command execution is exposed.
- Integrations use public APIs, SDKs, contracts, or explicit adapters; no private cross-repository imports are required.
- Tool execution crosses the centralized `GovernanceGate` for authentication, approval, policy, audit, and bounded-concurrency enforcement.
- External/untrusted content is represented using explicit evidence/trust boundaries and is not treated as instructions.

## Tool surface

Always available:

- `yasin_docs_*` — documentation access
- `yasin_github_*` — read-only GitHub ecosystem access
- `yasin_registry_*` — project/dependency registry access
- `yasin_gov_*` — governance reference capabilities used to exercise policy/approval boundaries

Conditionally available:

- `yasin_operations_*` — registered only when the `yasin-operations` executable is available on `PATH`.

The capability surface is versioned independently through `CAPABILITY_SURFACE_VERSION`.

## Evidence model

Responses that report ecosystem state use one of:

- `CONFIRMED` — directly observed from a live authoritative source
- `TARGET` — documented intent/architecture, not verified live
- `PROPOSED` — suggestion or plan, not implemented
- `UNRESOLVED` — could not be determined; never present this as fact

## Security and governance

Yasin-MCP treats documentation, GitHub content, registry content, and Operations output as external/untrusted data. Structural trust/evidence envelopes preserve the distinction between retrieved data and instructions.

The governance path is centralized and fail-closed. Authentication is established at the boundary; approval is explicit for mutation-risk reference capabilities; policy decisions are audited; structured errors are used at public boundaries; and configured concurrency is bounded.

## Transport

### stdio

The standard MCP stdio transport is supported and covered by the repository's live client/CLI validation surface.

### Streamable HTTP

Remote transport is implemented through an ASGI application and supports bearer authentication. Stage 13 provides live local verification using the official MCP Python client, with a real `ClientSession`, Streamable HTTP connection, authentication, context propagation, governance, approval, execution, and audit correlation.

Remote deployments require TLS unless `remote_allow_insecure_http` is explicitly enabled for local testing.

## Packaging and supported runtimes

`pyproject.toml` declares:

- package version: `0.1.0`
- `requires-python = ">=3.10"`
- `mcp>=2,<3`
- `PyYAML>=6,<7`

CI validates Python 3.10, 3.11, and 3.12 with Ruff, Mypy, Bandit, and pytest.

Native Termux Python 3.14.x remains unsupported/unverified because of the documented external `cryptography` ABI limitation. This does not change the normal supported CPython range.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
mypy src
bandit -q -r src
```

## Documentation index

| Doc | Purpose |
|-----|---------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture and evidence map |
| [RUNBOOK.md](docs/RUNBOOK.md) | Install, run, diagnose, and failure modes |
| [RELEASE_READINESS.md](docs/RELEASE_READINESS.md) | Final roadmap/release-readiness assessment |
| [STAGE5_PRODUCTION_READINESS.md](docs/STAGE5_PRODUCTION_READINESS.md) | Historical Stage 5 assessment |
| [GOVERNANCE.md](docs/GOVERNANCE.md) | Governance model |
| [CLIENT_RUNTIME.md](docs/CLIENT_RUNTIME.md) | Stdio client configuration and smoke checklist |
| [CAPABILITY_SURFACE.md](docs/CAPABILITY_SURFACE.md) | Capability surface/version semantics |
| [LIVE_MCP_HARNESS.md](docs/LIVE_MCP_HARNESS.md) | Live runtime evidence |
| [OPERATIONS_INTEGRATION.md](docs/OPERATIONS_INTEGRATION.md) | Optional Operations gateway |
| [REGISTRY_INTEGRATION.md](docs/REGISTRY_INTEGRATION.md) | Registry consumer contract |
| [RELIABILITY.md](docs/RELIABILITY.md) | Retry/reliability policy |
| [OBSERVABILITY.md](docs/OBSERVABILITY.md) | Correlation and redaction |
| [CHANGELOG.md](CHANGELOG.md) | Notable changes |

## Final roadmap rule

Master #96 defines the current five-issue completion roadmap. Stage 15 is its final planned stage. Future maintenance or genuinely new product features may be added later, but omitted roadmap work must not be hidden under a new Stage 16.
