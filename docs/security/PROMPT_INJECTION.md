# MCP Prompt Injection and Untrusted Context Hardening

**Status:** CONFIRMED enforcement on content-bearing return paths (P2-1 / Issue #62).

## Primary control (structural)

Every content-bearing adapter payload returned through MCP tools includes:

| Field | Meaning |
|-------|---------|
| `untrusted` | Always `true` for external data |
| `trust.untrusted` | Explicit trust block |
| `trust.content_role` | Always `data_only` |
| `trust.label` | `[UNTRUSTED_EXTERNAL_CONTENT]` |
| `trust.instruction_boundary` | Explicit instruction/data separation text |
| `trust.trust` | `never_elevated_by_sanitization` |
| `trust.suspicious_markers_detected` | Secondary diagnostic only |
| `trust.source_kind` | Origin classifier (`yasin-docs`, `github`, …) |

Original content fields are **preserved as data**. They are not rewritten into
trusted instructions. Clients and agents MUST treat these payloads as data.

## Secondary diagnostic

Keyword marker detection (`ignore previous instructions`, etc.) sets
`suspicious_markers_detected`. This is **not** a primary defense and does not
claim content is safe when false.

## Non-claims

- Labeling does **not** make hostile content trustworthy.
- Absence of markers does **not** imply safe content.
- Sanitization does **not** elevate trust.

## Coverage

| Source | Enforcement |
|--------|-------------|
| YASIN-DOCS document bodies | `Document.as_dict()` |
| YASIN-DOCS document refs | `_ref_to_dict()` |
| GitHub metadata / messages | `_meta()` + free-text markers |
| Project registry metadata | `ProjectMetadata.as_dict()` |
| Operations gateway data | `OperationsResult.as_dict()` |

See `yasin_mcp.security.untrusted_context`.
