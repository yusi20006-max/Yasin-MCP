# Yasin-MCP Architecture (Post-P2)

**Document status:** CONFIRMED against source at main (post-P2 audit).
**Evidence classes used below:** CONFIRMED | PARTIAL | TARGET | PROPOSED | UNRESOLVED

## Layered data flow

```
MCP Client (stdio)
  → MCP Runtime (ServerRuntime / MCPServer)
    → Capability / Tool Surface (CapabilityRegistry + surface_info)
      → Tools (docs / github / registry / operations*)
        → Adapters (read-only)
          → External sources (GitHub API, YASIN-DOCS via GitHub, optional yasin-operations gateway)
```

`*` Operations tools register only when `yasin-operations` is on PATH.

## Always-on vs optional tools

| Prefix | Registration | Evidence |
|--------|--------------|----------|
| `yasin_docs_*` | Always | CONFIRMED (runtime.py) |
| `yasin_github_*` | Always | CONFIRMED |
| `yasin_registry_*` | Always | CONFIRMED |
| `yasin_operations_*` | Optional PATH check | CONFIRMED (`operations_available` in `surface_info`) |

## Capability surface version

- Package: `yasin_mcp.version.__version__` (0.1.0)
- Surface: `CAPABILITY_SURFACE_VERSION` = `1.1.0`
- Discovery: `surface_metadata()` / `ServerRuntime.create().surface_info()`
- Bump surface version when always-on tool **names** or **schemas** change.

Evidence: CONFIRMED in `capabilities/surface.py`, `server/runtime.py`, tests.

## Trust boundaries

1. **Deny-by-default policy** (`policies/policy.py`) — CONFIRMED at capability construction.
2. **Read-only Phase boundary** — no mutation tools; Operations allow-list is fixed four ops — CONFIRMED.
3. **Untrusted external content** — structural `attach_untrusted_envelope` on adapter `as_dict` paths (docs, github entity types, registry, operations results) and tool fallbacks — CONFIRMED for primary paths; residual list wrappers tightened post-P2 audit.
4. **Keyword markers are secondary** — primary control is the structural envelope (`untrusted` + `trust`), not keyword detection alone.

## Evidence model

Responses use `EvidenceStatus`: CONFIRMED | TARGET | PROPOSED | UNRESOLVED (`version.py`).

## Request correlation

- Helpers: `request_scope`, `get_request_id`, `run_traced`, redacting `log_with_context` — CONFIRMED unit evidence.
- Propagation into Operations gateway request_id and GitHub rate-limit retry logs — CONFIRMED.
- Automatic wrap of every MCP tool invocation under `request_scope` — PARTIAL (helpers exist; not a mandatory middleware on all tools).

## Reliability

- `ReliabilityPolicy.max_retries` capped at 2 — CONFIRMED.
- GitHub HTTP: retries **only** for 403/429 rate-limit via `github_get_json` — CONFIRMED.
- Timeouts do **not** retry by default — CONFIRMED.
- No caching layer — CONFIRMED (absent by design).

## Registry contract

Consumer of YASIN-DOCS `PROJECT_REGISTRY.yaml` via docs adapter. See `REGISTRY_INTEGRATION.md`.
Missing file → `UnavailableDependencyError` (runtime UNRESOLVED). Invalid YAML → `ValidationError`.
Evidence: CONFIRMED unit tests; live content depends on upstream docs repo (OPTIONAL_LIVE / network).

## Live vs mocked evidence

| Class | Meaning |
|-------|---------|
| DEFAULT_CI | pytest + ruff + mypy + bandit; secret-free |
| LIVE_RUNTIME | Real stdio MCP client harness (`test_live_mcp_client_harness.py`) |
| OPTIONAL_LIVE | Real GitHub/YASIN-DOCS network calls when token/network present |
| UNIT/MOCK | Adapter tests with fake requesters / fake docs |

## Explicit non-claims

| Claim | Classification |
|-------|----------------|
| Generic MCP stdio compatibility | CONFIRMED (LIVE_RUNTIME harness) |
| Hermes live integration | UNRESOLVED (no Hermes in this repo; no mandatory dep) |
| Yasin-Agent live integration | UNRESOLVED (contract documented; no live agent run here) |
| Production-ready | Not claimed by this document |
| Live upstream always green in CI | Not claimed; CI is secret-free |

## Integration map

| Target | Mechanism | Evidence |
|--------|-----------|----------|
| YASIN-DOCS | GitHub contents API via docs adapter | Unit + optional live network |
| GitHub | Public REST API, bounded | Unit + optional live network |
| Project registry | File via docs adapter | Unit |
| Yasin-Operations | Subprocess JSONL gateway | Unit + fake/absent PATH |
| Hermes / Agent | Standard MCP stdio only | Generic protocol CONFIRMED; vendor-specific UNRESOLVED |
