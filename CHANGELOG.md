# Changelog

## [Unreleased]

### Added

- Stage 15 final roadmap-completion assessment and consolidated release-readiness evidence.
- Final documentation of packaging, supported runtimes, transport evidence, governance/auth/approval guarantees, limitations, and roadmap closure.
- Stage 14: bounded governed concurrency and deterministic lifecycle-resilience coverage.
- Stage 13: live ecosystem integration boundary and remote asserted-context propagation (Issue #99).
- Live Yasin-Agent-compatible Streamable HTTP client evidence for authentication, governance, approval, and audit correlation.
- `docs/STAGE13_LIVE_ECOSYSTEM_INTEGRATION.md`.
- Stage 10: live MCP stdio validation of auth enforcement and ToolError contract (Issue #94).
- Process-scoped `YASIN_MCP_PRESENT_AUTH_TOKEN` for stdio parent presentation.
- Stage 9: structured MCP ToolError contract + credential transport abstraction (Issue #92).
- `docs/STAGE9_SECURITY_AND_TRANSPORT.md`.
- Stage 8: mandatory authentication enforcement on GovernanceGate execution path.
- `docs/STAGE8_AUTH_ENFORCEMENT.md`.
- Stage 7.1 authentication boundary: stdio peer UNRESOLVED, optional shared-secret.
- `docs/STAGE7_AUTHENTICATION.md`.

### Changed

- README now reflects the final five-issue roadmap state and supported evidence boundaries.
- Remote transport validates and binds optional `X-Yasin-Context` as ASSERTED request context before the existing authentication/governance path.
- GovernanceGate maps McpError to SDK ToolError on the MCP wrap path.
