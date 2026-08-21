# YASIN-DOCS Canonical Context Integration

**Status:** CONFIRMED for adapter + MCP tool wiring (Issue #38).  
**Contract:** public GitHub Contents/Trees API for fixed repository `yusi20006-max/YASIN-DOCS` @ `main`.

## Boundary

```
MCP Client
    ↓
Yasin-MCP docs tools (yasin_docs_*)
    ↓
YasinDocsAdapter (fixed owner/repo/ref)
    ↓
GitHub REST API (public, optional token)
    ↓
YASIN-DOCS repository tree and file bodies
```

Callers cannot redirect the adapter to an arbitrary URL or repository. Network I/O is injectable for tests.

## Tools (always registered)

| Tool | Purpose |
|------|---------|
| `yasin_docs_list_documents` | Bounded text document paths from the tree |
| `yasin_docs_get_document` | Read one path |
| `yasin_docs_search` | Case-insensitive body search; optional `path_prefix` |
| `yasin_docs_list_adrs` | Paths under `docs/adr/` |
| `yasin_docs_get_adr` | ADR by short name or path |
| `yasin_docs_list_architecture` | `ARCHITECTURE.md` + `docs/architecture/*` |
| `yasin_docs_get_project_architecture` | Best-effort match; does not invent missing docs |

## Evidence model

| Layer | Status |
|-------|--------|
| File path exists in live tree / API returns content | **CONFIRMED** |
| Claims *inside* architecture/ADR bodies | **TARGET** (documentation intent) unless independently verified |
| Missing path | structured `NotFoundError` — not a hallucinated document |

Every successful document payload includes `provenance` (`source`, `repository`, `ref`, `path`, `sha`, `source_url`) and `evidence_status`.

## Limitations (UNRESOLVED / documented)

- Layout is the **public repository structure** observed on GitHub, not a separate versioned schema API.
- Without `GITHUB_TOKEN` / config token, unauthenticated rate limits may apply.
- Full-repository search iterates bounded `list_documents` then fetches bodies (cost scales with `max_files`).
- Live domain tool success against GitHub is **not** required for unit tests; tests inject a fake requester (**MOCKED_INTEGRATION**). Optional live validation is environment-dependent.

## Failure behavior

| Condition | Result |
|-----------|--------|
| Invalid path / traversal | `ValidationError` |
| Missing file | `NotFoundError` |
| Auth failure | `UnauthenticatedError` |
| Rate limit / 403 | `RateLimitedError` |
| Timeout | `TimeoutMcpError` |
| Network down | `UnavailableDependencyError` |
| Bad upstream JSON | `UpstreamError` |

Server continues to run; failures are per-tool structured errors.
