import pytest

from yasin_mcp.errors.errors import PolicyDeniedError
from yasin_mcp.policies.policy import (
    check_capability_name_allowed,
    check_mutation_allowed,
)

# -- Forbidden name patterns (the critical safety boundary) ----------------


@pytest.mark.parametrize(
    "forbidden_name",
    [
        "execute",
        "exec",
        "run_shell_command",
        "shell",
        "shell_exec",
        "command",
        "request",
        "arbitrary_api",
        "arbitrary_execute",
        "filesystem",
        "filesystem_write",
        "deploy",
        "deploy_service",
        "delete",
        "delete_repo",
        "start_service",
        "stop_service",
        "restart_service",
    ],
)
def test_forbidden_names_are_rejected(forbidden_name):
    with pytest.raises(PolicyDeniedError):
        check_capability_name_allowed(forbidden_name)


@pytest.mark.parametrize(
    "forbidden_name",
    [
        "EXECUTE",
        "Shell",
        "COMMAND",
        "Arbitrary",
    ],
)
def test_forbidden_names_are_case_insensitive(forbidden_name):
    with pytest.raises(PolicyDeniedError):
        check_capability_name_allowed(forbidden_name)


@pytest.mark.parametrize(
    "safe_name",
    [
        "list_projects",
        "get_project",
        "get_ecosystem_status",
        "search_docs",
        "get_doc",
        "get_adr",
        "list_repositories",
        "get_repository",
        "search_code",
        "get_issue",
        "list_issues",
        "get_pull_request",
        "get_ci_status",
        "get_runtime_status",
        "get_project_health",
        "get_capabilities",
        "get_diagnostics",
    ],
)
def test_expected_phase_1_capability_names_are_allowed(safe_name):
    # Must not raise
    check_capability_name_allowed(safe_name)


def test_policy_denied_error_includes_name_in_details():
    try:
        check_capability_name_allowed("shell_command")
    except PolicyDeniedError as exc:
        assert exc.details.get("name") == "shell_command"
    else:
        pytest.fail("expected PolicyDeniedError")


# -- Mutation boundary (runtime governance) ----------------------------------


def test_mutation_is_delegated_to_runtime_governance():
    # Stage 11 intentionally lifts the registration-time mutation ban.
    # Runtime GovernanceGate remains responsible for authorization.
    check_mutation_allowed(is_mutating=True)


def test_non_mutation_allowed():
    # Must not raise
    check_mutation_allowed(is_mutating=False)
