"""Independence and import-hygiene tests.

Confirms the package imports cleanly with zero dependency on any
other Yasin repository, and statically guards against a future
accidental import of a private module from another Yasin repo.
"""

import ast
import pathlib

from yasin_mcp.config.config import ServerConfig, load_config
from yasin_mcp.errors.errors import ErrorCategory, McpError
from yasin_mcp.policies.policy import check_capability_name_allowed
from yasin_mcp.version import EvidenceStatus, __version__


def test_version_is_defined():
    assert __version__ == "0.1.0"


def test_full_import_flow_works():
    config = load_config()
    assert isinstance(config, ServerConfig)

    err = McpError(category=ErrorCategory.NOT_FOUND, message="x")
    assert err.category == ErrorCategory.NOT_FOUND

    check_capability_name_allowed("get_project")  # must not raise

    assert EvidenceStatus.CONFIRMED.value == "confirmed"


def test_no_import_of_other_yasin_repositories():
    """Static guard: no real import statement may reference another
    Yasin repository's package name. Docstrings/comments mentioning
    these names (to explain the boundary) are not a violation --
    only actual import/from statements are checked.
    """
    package_root = pathlib.Path(__file__).parent.parent / "src" / "yasin_mcp"
    forbidden_substrings = (
        "yasin_core",
        "yasincore",
        "yasin_agent",
        "yasinagent",
        "yasinai",
        "yasin_ai",
        "yasinhub",
        "yasincli",
        "yasin_operations",
        "yasinoperations",
    )

    offending = []
    for path in package_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module_names: list[str] = []
            if isinstance(node, ast.Import):
                module_names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                module_names = [node.module]

            for name in module_names:
                lowered = name.lower()
                for term in forbidden_substrings:
                    if term in lowered:
                        offending.append((str(path), name))

    assert offending == [], f"Found forbidden import references: {offending}"
