"""Stage 10 / Issue #94 — live MCP stdio validation of Stages 7–9 guarantees.

Evidence class: LIVE — real yasin-mcp subprocess + MCP Python client over stdio.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from yasin_mcp.tools.docs import TOOL_LIST_DOCS

SECRET = "TEST_STAGE10_LIVE_SECRET"


def _yasin_mcp() -> str:
    which = shutil.which("yasin-mcp")
    if which:
        return which
    for base in (Path(sys.argv[0]).resolve().parent, Path(sys.prefix) / "bin"):
        candidate = base / "yasin-mcp"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    pytest.skip("yasin-mcp console script not available")


def _error_text(result: Any) -> str:
    parts: list[str] = []
    content = getattr(result, "content", None) or []
    for item in content:
        text = getattr(item, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


def _is_error(result: Any) -> bool:
    return bool(getattr(result, "isError", None) or getattr(result, "is_error", None))


def _parse_contract(text: str) -> dict[str, Any] | None:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict) and "code" in data:
        return data
    return None


async def _session(env: dict[str, str]) -> dict[str, Any]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=_yasin_mcp(), args=[], env=env)
    out: dict[str, Any] = {"clean": False}
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            out["protocol"] = getattr(init, "protocolVersion", None) or getattr(
                init, "protocol_version", None
            )
            tools = getattr(await session.list_tools(), "tools", []) or []
            names = [getattr(t, "name", "") for t in tools]
            out["tool_count"] = len(tools)
            out["has_list_docs"] = TOOL_LIST_DOCS in names

            unk = await session.call_tool("yasin_mcp_nonexistent_tool_xyz", arguments={})
            out["unknown_is_error"] = _is_error(unk)
            out["unknown_text"] = _error_text(unk)

            call = await session.call_tool(TOOL_LIST_DOCS, arguments={})
            out["list_is_error"] = _is_error(call)
            out["list_text"] = _error_text(call)
            out["list_contract"] = _parse_contract(out["list_text"])

            call2 = await session.call_tool(TOOL_LIST_DOCS, arguments={})
            out["list2_is_error"] = _is_error(call2)
            out["list2_text"] = _error_text(call2)
            out["list2_contract"] = _parse_contract(out["list2_text"])

    out["clean"] = True
    return out


def test_live_compat_mode_allows_read_only_and_unknown_errors() -> None:
    env = {**os.environ}
    env.pop("YASIN_MCP_REQUIRE_AUTH", None)
    env.pop("YASIN_MCP_AUTH_TOKEN", None)
    env.pop("YASIN_MCP_PRESENT_AUTH_TOKEN", None)
    res = asyncio.run(_session(env))
    assert res["protocol"]
    assert res["has_list_docs"]
    assert res["unknown_is_error"] is True
    assert res["clean"] is True
    if res["list_is_error"]:
        assert SECRET not in res["list_text"]
    else:
        assert res["list2_is_error"] is False


def test_live_require_auth_missing_credential_blocks() -> None:
    env = {
        **os.environ,
        "YASIN_MCP_AUTH_TOKEN": SECRET,
        "YASIN_MCP_REQUIRE_AUTH": "true",
    }
    env.pop("YASIN_MCP_PRESENT_AUTH_TOKEN", None)
    res = asyncio.run(_session(env))
    assert res["list_is_error"] is True
    contract = res["list_contract"]
    assert contract is not None, res["list_text"]
    assert contract["code"] == "AUTHENTICATION_REQUIRED"
    assert SECRET not in res["list_text"]
    assert "traceback" not in res["list_text"].lower()
    assert res["list2_is_error"] is True
    assert res["clean"] is True


def test_live_require_auth_invalid_credential_blocks() -> None:
    env = {
        **os.environ,
        "YASIN_MCP_AUTH_TOKEN": SECRET,
        "YASIN_MCP_REQUIRE_AUTH": "true",
        "YASIN_MCP_PRESENT_AUTH_TOKEN": "WRONG_SECRET_VALUE",
    }
    res = asyncio.run(_session(env))
    assert res["list_is_error"] is True
    contract = res["list_contract"]
    assert contract is not None, res["list_text"]
    assert contract["code"] in {"AUTHENTICATION_FAILED", "AUTHENTICATION_REQUIRED"}
    assert SECRET not in res["list_text"]
    assert "WRONG_SECRET_VALUE" not in res["list_text"]
    assert res["clean"] is True


def test_live_require_auth_valid_credential_allows_read_only() -> None:
    env = {
        **os.environ,
        "YASIN_MCP_AUTH_TOKEN": SECRET,
        "YASIN_MCP_REQUIRE_AUTH": "true",
        "YASIN_MCP_PRESENT_AUTH_TOKEN": SECRET,
        "YASIN_MCP_AUTH_SUBJECT": "local-operator",
    }
    res = asyncio.run(_session(env))
    assert res["clean"] is True
    assert SECRET not in res["list_text"]
    if res["list_is_error"]:
        contract = res["list_contract"]
        if contract:
            assert contract["code"] not in {
                "AUTHENTICATION_REQUIRED",
                "AUTHENTICATION_FAILED",
            }
    else:
        assert res["list2_is_error"] is False


def test_live_sequential_sessions_auth_isolation() -> None:
    fail_env = {
        **os.environ,
        "YASIN_MCP_AUTH_TOKEN": SECRET,
        "YASIN_MCP_REQUIRE_AUTH": "true",
    }
    fail_env.pop("YASIN_MCP_PRESENT_AUTH_TOKEN", None)
    ok_env = {
        **os.environ,
        "YASIN_MCP_AUTH_TOKEN": SECRET,
        "YASIN_MCP_REQUIRE_AUTH": "true",
        "YASIN_MCP_PRESENT_AUTH_TOKEN": SECRET,
    }
    first = asyncio.run(_session(fail_env))
    second = asyncio.run(_session(ok_env))
    assert first["list_is_error"] is True
    assert first["list_contract"] and first["list_contract"]["code"] == "AUTHENTICATION_REQUIRED"
    assert second["clean"] is True
    if second["list_contract"]:
        assert second["list_contract"]["code"] != "AUTHENTICATION_REQUIRED"


def test_live_repeated_sessions_compat() -> None:
    env = {**os.environ}
    env.pop("YASIN_MCP_REQUIRE_AUTH", None)
    a = asyncio.run(_session(env))
    b = asyncio.run(_session(env))
    assert a["tool_count"] == b["tool_count"]
    assert a["clean"] and b["clean"]
