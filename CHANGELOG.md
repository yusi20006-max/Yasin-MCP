# Changelog

All notable changes to Yasin-MCP are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Stage 6 integration context contract, trust classification, and isolation tests (Issue #87).
- `docs/STAGE6_INTEGRATION.md` ecosystem integration boundary documentation.

- Stage 5 production-readiness tests: capability surface integrity, repeated MCP sessions, failure recovery, CLI config exit path (Issue #84).
- `docs/STAGE5_PRODUCTION_READINESS.md` assessment.

### Changed

- CLI exits with code 2 and a secret-free message on invalid configuration instead of an uncaught traceback (Issue #84).

## [0.1.0] — Stages 1–4 baseline

### Added

- Termux / native Android + CPython 3.14 compatibility boundary (Issue #78).
- MCP Governance Layer with centralized `GovernanceGate` (Issue #80).
- Security hardening, fail-closed proofs, and audit exception-type-only recording (Issue #82).
- Live MCP stdio client harness and quality CI matrix (Python 3.10–3.12).

### Security

- Deny-by-default unknown tools; DENY and APPROVAL_REQUIRED never execute underlying tools.
- Secret redaction for audit and structured logs.
