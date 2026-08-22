from __future__ import annotations

import importlib
import sysconfig
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _is_native_termux() -> bool:
    soabi = sysconfig.get_config_var("SOABI") or ""
    platform = sysconfig.get_platform() or ""
    return "android" in soabi.lower() or "android" in platform.lower()


def test_readme_documents_native_termux_limitation() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "native Termux" in text
    assert "Python 3.14" in text
    assert "PyLong_Type" in text
    assert "unsupported" in text.lower()


def test_runbook_documents_termux_boundary() -> None:
    text = (ROOT / "docs" / "RUNBOOK.md").read_text(encoding="utf-8")

    assert "Termux / Android compatibility boundary" in text
    assert "cryptography" in text
    assert "PyLong_Type" in text
    assert "proot-distro Debian" in text


@pytest.mark.skipif(
    _is_native_termux(),
    reason="native Termux is outside the verified runtime boundary",
)
def test_cryptography_rust_extension_loads_on_supported_ci() -> None:
    module = importlib.import_module("cryptography.hazmat.bindings._rust")
    assert module is not None


@pytest.mark.skipif(
    _is_native_termux(),
    reason="native Termux is outside the verified runtime boundary",
)
def test_mcp_imports_on_supported_ci() -> None:
    module = importlib.import_module("mcp")
    assert module is not None
