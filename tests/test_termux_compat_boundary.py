from __future__ import annotations

import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_documents_native_termux_verification() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Native Termux compatibility is verified" in text
    assert "Python 3.14" in text
    assert "Termux" in text


def test_runbook_documents_termux_boundary() -> None:
    text = (ROOT / "docs" / "RUNBOOK.md").read_text(encoding="utf-8")

    assert "Termux / Android compatibility boundary" in text
    assert "cryptography" in text
    assert "PyLong_Type" in text


def test_cryptography_rust_extension_loads() -> None:
    module = importlib.import_module("cryptography.hazmat.bindings._rust")
    assert module is not None


def test_mcp_imports() -> None:
    module = importlib.import_module("mcp")
    assert module is not None
