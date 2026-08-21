"""Capability surface version metadata (P2-3)."""

from yasin_mcp.capabilities.surface import SURFACE_NAME, surface_metadata
from yasin_mcp.version import CAPABILITY_SURFACE_VERSION, __version__


def test_surface_metadata_is_deterministic() -> None:
    meta = surface_metadata()
    assert meta["package_version"] == __version__
    assert meta["capability_surface_version"] == CAPABILITY_SURFACE_VERSION
    assert meta["surface_name"] == SURFACE_NAME
    assert meta["phase"] == "read_only"
    assert "yasin_docs_" in meta["always_on_prefixes"]
    assert "yasin_operations_" in meta["optional_prefixes"]


def test_runtime_exposes_surface_info() -> None:
    from yasin_mcp.server.runtime import ServerRuntime

    runtime = ServerRuntime.create()
    info = runtime.surface_info()
    assert info["capability_surface_version"] == CAPABILITY_SURFACE_VERSION
