# Changelog

## [Unreleased]

### Added

- Stage 10: live MCP stdio validation of auth enforcement and ToolError contract (Issue #94).
- Process-scoped `YASIN_MCP_PRESENT_AUTH_TOKEN` for stdio parent presentation.
- Stage 9: structured MCP ToolError contract + credential transport abstraction (Issue #92).
- `docs/STAGE9_SECURITY_AND_TRANSPORT.md`.
- Stage 8: mandatory authentication enforcement on GovernanceGate execution path.
- `docs/STAGE8_AUTH_ENFORCEMENT.md`.
- Stage 7.1 authentication boundary: stdio peer UNRESOLVED, optional shared-secret.
- `docs/STAGE7_AUTHENTICATION.md`.

### Changed

- GovernanceGate maps McpError to SDK ToolError on the MCP wrap path.
