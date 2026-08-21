# GitHub Ecosystem Intelligence Integration

**Status:** CONFIRMED for adapter + MCP tool wiring (Issue #39).  
**Contract:** public GitHub REST API (`api.github.com`), optional bearer token.

## Boundary

```
MCP Client → yasin_github_* tools → GitHubAdapter → GitHub REST API
```

No write methods. No generic request passthrough. Repository identifiers are validated (no path traversal).

## Tools (always registered)

| Tool | Purpose |
|------|---------|
| `yasin_github_get_repository` | Repo metadata |
| `yasin_github_list_issues` / `get_issue` | Issues |
| `yasin_github_list_pull_requests` / `get_pull_request` | PRs |
| `yasin_github_list_commits` | Recent commits |
| `yasin_github_get_commit_status` | Combined status |
| `yasin_github_list_workflow_runs` | CI runs |
| `yasin_github_list_branches` | Branches |
| `yasin_github_list_releases` | Releases |

## Evidence

Successful API responses are **CONFIRMED** with `provenance.source = "github"`.  
Unit tests use injected requesters (**MOCKED_INTEGRATION**). Live GitHub calls are environment-dependent and optional.

## Failure mapping

401 → UnauthenticatedError · 403/429 → RateLimitedError · 404 → NotFoundError · timeout → TimeoutMcpError · network → UnavailableDependencyError
