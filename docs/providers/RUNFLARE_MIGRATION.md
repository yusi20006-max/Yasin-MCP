# Runflare Migration Status

## Source

`yusi20006-max/Yasin-Runflare-MCP`

## Active target

`yusi20006-max/Yasin-MCP`

## Status

The Runflare provider has been migrated into Yasin-MCP through the phased implementation:

1. capability registry and governance
2. scoped tools
3. security hardening
4. mock/fake CLI regression tests
5. official CLI compatibility validation
6. Hermes integration contract validation
7. documentation and permission audit

Phases 8–9 are the release and final audit gates.

## Compatibility contract

Authentication remains owned by the official Runflare CLI. Yasin-MCP supplies only the explicitly configured project target and invokes fixed provider operations.

## Repository retention

The standalone repository is intentionally retained for reference and is not deleted by migration work.
