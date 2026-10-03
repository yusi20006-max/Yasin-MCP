"""Compatibility probes for the documented Runflare CLI contract.

The probes are deliberately read-only: they inspect version/help output and
never execute a deployment or lifecycle mutation.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

EXPECTED_COMMANDS = ("deploy", "events", "logs", "start", "restart", "stop")
EXPECTED_FLAGS = {
    "deploy": ("-y",),
    "events": ("-y",),
    "logs": ("-y",),
    "start": ("-y",),
    "restart": ("-y",),
}


@dataclass(frozen=True)
class CompatibilityReport:
    version: str
    help_text: str
    missing_commands: tuple[str, ...]
    missing_flags: tuple[str, ...]
    compatible: bool


def _probe(binary: str, *args: str, timeout: int = 15) -> str:
    completed = subprocess.run(
        [binary, *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        shell=False,
    )
    output = (completed.stdout or "") + "\n" + (completed.stderr or "")
    if completed.returncode != 0:
        raise RuntimeError(f"Runflare compatibility probe failed: {args[0]}")
    return output


def probe_compatibility(binary: str | None = None) -> CompatibilityReport:
    """Inspect version/help only; no project or credentials are touched."""
    executable = binary or os.getenv("RUNFLARE_BIN") or "runflare"
    version = _probe(executable, "--version")
    help_text = _probe(executable, "--help")

    missing_commands = tuple(command for command in EXPECTED_COMMANDS if command not in help_text)
    missing_flags: list[str] = []
    for command, flags in EXPECTED_FLAGS.items():
        command_help = _probe(executable, command, "--help")
        for flag in flags:
            if flag not in command_help:
                missing_flags.append(f"{command}:{flag}")

    return CompatibilityReport(
        version=version.strip(),
        help_text=help_text,
        missing_commands=missing_commands,
        missing_flags=tuple(missing_flags),
        compatible=not missing_commands and not missing_flags,
    )
