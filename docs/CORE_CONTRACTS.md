# Yasin-Core Shared-Contract Compatibility (Post-Core Integration)

## 1. Audit result (Yasin-MCP @ v1.0.0, post Yasin-Core v3.4.0)

**Already complete — not repeated:**

- MCP server (stdio + authenticated remote transport with `/healthz`/`/readyz`),
  CLI (`yasin-mcp --help/--version`), runtime, capability registry (22 tools),
  governance/approval/auth layers, adapters (YASIN-DOCS, GitHub, Operations
  subprocess gateway, project registry), protocol contracts, reliability,
  observability, security (untrusted-context envelope, secret-free client
  error contract), config, packaging, 30+ docs, CI, Termux/Android boundary.
- Zero `yasin_core` imports in `src/` (enforced by
  `tests/test_independence.py` and `tests/test_phase1_matrix.py`).
- No Control Plane behavior: all Operations tools are read-only by
  construction; no lifecycle/process ownership.

**Already compatible:**

- Adapter-based integration only (no private cross-repo imports) — matches
  Core's consumer rule: import only from `yasin_core.sdk`.
- `docs/RELEASE_READINESS.md` boundary statement intact.

**Real integration gap found (exactly one):**

- Yasin-MCP could not speak Yasin-Core v3.4.0's shared observation
  vocabulary (`HealthReport`, `ServiceStatus`, `ErrorInfo`, secret
  redaction, contract registry `1.1.0`). Its native models
  (`HealthStatus.status: str`, `OperationsResult.status: str`,
  `ErrorCategory`) overlap the same problem space with different
  shapes/values, forcing every ecosystem consumer to hand-translate.

**Not gaps (deliberately left alone):**

- Native MCP models are kept as-is (backward compatibility).
- `ControlResult` is intentionally *not* produced here — lifecycle verdicts
  belong to the Control Plane (YasinHub). See mapping table below.

## 2. Architecture decision

Additive, dependency-free compatibility layer — `src/yasin_mcp/compat/`:

```text
Yasin-Core (v3.4.0, contract registry 1.1.0)
    ↓ shared contracts (read models only, via yasin_core.sdk)
Yasin-MCP compat layer (pure translators, NO yasin_core import)
    ↓ Core-shaped dicts (HealthReport / ServiceStatus / ErrorInfo)
MCP clients / ecosystem consumers
```

- **No new dependency**: `yasin-core` is NOT in `pyproject.toml`.
  Compatibility is proven by `tests/test_core_contracts_compat.py`, whose
  live round-trip parses our dicts with the real `yasin_core.sdk` when
  Core ≥ 3.4.0 is installed and skips otherwise.
- **No private Core imports**: not even `yasin_core.contracts` (Core
  forbids it for consumers); the canonical boundary `yasin_core.sdk`
  is referenced by name only in docs/tests.
- **No behavior change**: translators are pure functions beside the
  native models; existing tools, schemas, and error payloads are untouched.

## 3. Mapping tables (Yasin-Core v3.4.0, registry 1.1.0)

### Health: MCP `HealthStatus.status` → Core `HealthState`

| MCP token (case-insensitive) | Core `HealthState` |
|---|---|
| `healthy`, `ok`, `up` | `HEALTHY` |
| `degraded` | `DEGRADED` |
| `unhealthy`, `failed`, `failure`, `error`, `down` | `UNHEALTHY` |
| anything else (`unresolved`, `unknown`, `running`, empty, …) | `UNKNOWN` |

Never guesses `HEALTHY` — mirrors Core's `HealthReport.is_healthy` rule.

### Status: MCP `OperationsResult.status` → Core `ServiceStatusValue`

Case-insensitive passthrough for `RUNNING / STOPPED / FAILED / UNKNOWN /
IDLE / SUCCESS / STALE`; anything else → `UNKNOWN`. Non-positive or
non-integer PIDs drop to `None` (MCP never fabricates process identity).

### Errors: MCP `ErrorCategory` → Core `ErrorCode`

| MCP `ErrorCategory` | Core `ErrorCode` |
|---|---|
| `VALIDATION_ERROR` | `INVALID` |
| `NOT_FOUND` | `NOT_FOUND` |
| `TIMEOUT` | `TIMEOUT` |
| `UNAVAILABLE_DEPENDENCY`, `UPSTREAM_ERROR` | `UNAVAILABLE` |
| `UNAUTHENTICATED`, `UNAUTHORIZED`, `POLICY_DENIED` | `REFUSED` |
| `RATE_LIMITED` | `CONFLICT` |
| `INTERNAL_ERROR` | `UNKNOWN` |

Messages are redacted at build (same pattern set as Core's
`redact_secrets`); secret-named detail keys are dropped — mirroring
Core's `ErrorInfo` constructor guarantee.

### Ownership

| Concern | Owner |
|---|---|
| Shared contracts / models | Yasin-Core |
| Control Plane / lifecycle / `ControlResult` | YasinHub |
| Control-Plane client | YasinCLI |
| Tools / Resources / these translators | Yasin-MCP |

## 4. Verification

- `tests/test_core_contracts_compat.py`: 11 tests (coercion, shapes,
  validators, redaction, version pins, native-model invariance, live SDK
  round-trip). Full suite preserved (all pre-existing tests untouched).
- Termux/Android ARM64 (Python 3.14.6): package imports, `ServerRuntime`
  advertises 22 tools, diagnostics health maps `unresolved → UNKNOWN`,
  `yasin-mcp --help` exits 0, live round-trip against installed
  `yasin-core==3.4.0` passes.
- Quality gates: `pytest`, `mypy src`, `bandit`, `ruff` (CI).

## 5. Known limitations

- Translators mirror Core registry `1.1.0`; a future Core contract bump
  needs a re-check of `src/yasin_mcp/compat/core_contracts.py`
  (constants `CORE_CONTRACT_VERSION` / `CORE_VERSION_COMPAT`).
- Python 3.14 is outside Core's certified range (3.9–3.13); the
  dependency-free translators are unaffected, live SDK interop on 3.14
  is verified opportunistically, not certified.
