# Capability Surface Version

**Status:** CONFIRMED (P2-3)

## Versions

| Field | Source | Meaning |
|-------|--------|---------|
| `package_version` | `yasin_mcp.version.__version__` | Python package release |
| `capability_surface_version` | `CAPABILITY_SURFACE_VERSION` | Client-visible tool/capability set |
| MCP protocol version | Negotiated at initialize | Transport protocol |

## Semantics

- Bump `CAPABILITY_SURFACE_VERSION` when always-on tool **names** or **schemas** change in a client-visible way.
- Package version may move independently (docs, tests, internals).
- Optional Operations tools may appear/disappear without a surface version bump when the gateway is absent.

## Discovery

```python
from yasin_mcp.capabilities.surface import surface_metadata
from yasin_mcp.server.runtime import ServerRuntime

surface_metadata()
ServerRuntime.create().surface_info()
```

Server description embeds the surface version for initialize-time visibility.
