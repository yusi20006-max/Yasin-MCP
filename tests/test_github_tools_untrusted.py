"""Ensure GitHub tool return paths carry untrusted envelopes (P3 residual)."""

from __future__ import annotations

from yasin_mcp.adapters.github import GitHubAdapter
from yasin_mcp.tools.github import GitHubToolset


def test_list_workflow_runs_payload_is_untrusted() -> None:
    def requester(url: str, headers: dict[str, str], timeout: int):
        return {
            "workflow_runs": [
                {
                    "id": 1,
                    "name": "CI",
                    "status": "completed",
                    "conclusion": "success",
                    "html_url": "https://example/run/1",
                }
            ]
        }

    adapter = GitHubAdapter(requester=requester)
    tools = GitHubToolset(adapter)
    payload = tools.list_workflow_runs("o", "r", limit=5)
    assert payload.get("untrusted") is True
    assert "trust" in payload
    assert payload["workflow_runs"]
    assert payload["workflow_runs"][0].get("untrusted") is True
