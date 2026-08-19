# Yasin-MCP Security Threat Model

## Scope

This document defines the Phase 0 security boundary. It does not authorize any
mutation capability.

## Trust Boundaries

```text
MCP Client / AI Agent
        │ untrusted input
        ▼
Yasin-MCP Protocol Boundary
        │
        ├── Policy Gate
        ├── Contract Validation
        ├── Adapter Boundary
        └── Structured Error Boundary
                │
                ▼
        External Services / Yasin Projects
```

## Primary Threats

| Threat | Control |
|---|---|
| Arbitrary command execution | Forbidden-name policy + no execution API |
| Filesystem mutation | Forbidden capability names + no filesystem API |
| Accidental mutation | Phase 1 read-only gate |
| Secret leakage in logs | SecretStr + recursive log redaction |
| Secret leakage in errors | Structured error model; callers must not include credentials |
| Unbounded upstream calls | Validated adapter timeout bounds |
| Resource exhaustion | Bounded request concurrency configuration |
| Malformed capability contracts | Construction-time validation |
| Ambiguous capability state | Explicit safety class and evidence status |
| Cross-repository coupling | Public adapter boundary; no private imports |

## Security Principles

1. Deny by default.
2. Fail closed on invalid policy/configuration.
3. Never expose raw secrets through normal representations or logs.
4. Keep Phase 1 read-only.
5. Do not expose generic execution or arbitrary API passthrough.
6. Keep external integrations behind explicit adapters.
7. Preserve correlation IDs for diagnostic traceability.
8. Do not represent target architecture as runtime evidence.

## Future Mutation Boundary

Future mutation classes are vocabulary only in Phase 0.3:

- `PROPOSED_MUTATION`
- `CONFIRMED_MUTATION`

They remain denied while `PHASE_1_READ_ONLY` is enabled. A future phase must
introduce authorization, confirmation, audit, protected targets, and dry-run
semantics before enabling them.
