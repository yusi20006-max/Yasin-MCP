"""Narrow adapter around the official Runflare CLI.

The provider never exposes generic shell execution and never accepts
Runflare credentials through MCP arguments.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from .security import redact, validate_project_dir


@dataclass(frozen=True)
class CLIResult:
    returncode: int
    stdout: str
    stderr: str


class RunflareCLI:
    """Execute only documented, scoped Runflare CLI operations."""

    def __init__(self, project_dir: str | None = None) -> None:
        self.binary = os.getenv("RUNFLARE_BIN", "runflare")
        if os.path.basename(self.binary) != "runflare":
            raise ValueError("RUNFLARE_BIN must resolve to the official runflare executable")
        self.timeout = int(os.getenv("RUNFLARE_TIMEOUT_SECONDS", "120"))
        self.max_output = int(os.getenv("RUNFLARE_MAX_OUTPUT", "12000"))
        self.project_dir = validate_project_dir(
            project_dir or os.getenv("RUNFLARE_PROJECT_DIR", "")
        )

    def _run(self, *args: str) -> CLIResult:
        if any(not isinstance(arg, str) or "\x00" in arg for arg in args):
            raise ValueError("Invalid CLI argument")
        try:
            completed = subprocess.run(
                [self.binary, *args],
                cwd=self.project_dir,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
                shell=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Official Runflare CLI was not found") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Runflare CLI timed out") from exc
        return CLIResult(
            completed.returncode,
            redact(completed.stdout or "", self.max_output),
            redact(completed.stderr or "", self.max_output),
        )

    def status(self) -> CLIResult:
        return self._run("events", "-y")

    def deploy(self) -> CLIResult:
        return self._run("deploy", "-y")

    def logs(self, follow: bool = False) -> CLIResult:
        return self._run("logs", "-y", *(["-f"] if follow else []))

    def events(self, follow: bool = False) -> CLIResult:
        return self._run("events", "-y", *(["-f"] if follow else []))

    def restart(self) -> CLIResult:
        return self._run("restart", "-y")

    def start(self) -> CLIResult:
        return self._run("start", "-y")

    def stop(self) -> CLIResult:
        raise PermissionError(
            "runflare_stop requires explicit confirmation outside the MCP server"
        )
