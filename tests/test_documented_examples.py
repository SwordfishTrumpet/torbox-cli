"""Every documented invocation must actually parse.

Issue #39: six documented commands could not run. The cron and debug recipes in
the README placed the global-only `--quiet` / `--verbose` flags *after* the
subcommand, and the help text of the three `control` commands showed the
operation as a positional argument even though those commands accept it only
through `--operation`. Nothing verified the examples, so they drifted apart
from the CLI surface.

This module extracts every invocation from the README's bash blocks and from
each command's `Example:` help line, runs it against a stubbed API, and fails
on a command-line error (unknown option, extra argument, missing required
option, invalid value). Examples that cannot be executed in-process are skipped
explicitly, never silently.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tests.conftest import strip_ansi
from torbox.cli import app

runner = CliRunner()

README = (Path(__file__).resolve().parent.parent / "README.md").read_text(
    encoding="utf-8"
)

# Command-line errors click/typer reports before the command body runs. A
# command that fails *inside* its body (a missing local file, mock data with no
# hash) prints its own message and is not a parse failure.
PARSE_ERROR_MARKERS = (
    "No such option",
    "no such option",
    "No such command",
    "no such command",
    "unexpected extra argument",
    "Missing option",
    "Missing argument",
    "Invalid value for",
    "Requires an argument",
)

# Invocations that parse but cannot be executed here, each with its reason.
EXECUTION_EXCLUSIONS = {
    " monitor": "starts the interactive live monitor loop, which never returns",
    "--install-completion": "writes a completion file and edits the user's shell rc",
}

# The recipes the README highlights for automation, plus the examples that were
# broken. These must not merely parse: they must run to completion.
RECIPES = [
    "torbox --quiet torrents list --auto-retry --json",
    "torbox --quiet torrents list --json",
    "torbox --verbose general status",
    "torbox torrents control 42 --operation delete --yes",
    "torbox usenet control 10 --operation delete --yes",
    "torbox webdl control 20 --operation delete --yes",
    "torbox user delete --confirmation-code 123456 --session-token session-abc --yes",
]


def _invocation_on_line(line: str) -> str | None:
    """Return the ``torbox`` invocation on a README line, if there is one."""
    index = line.find("torbox ")
    if index == -1:
        return None
    segment = line[index:]
    # Keep only the torbox command: drop shell comments, pipes, redirections,
    # subshell wrappers and sequencing.
    segment = re.sub(r"\s+#.*$", "", segment)
    for separator in (" | ", " > ", " >> ", " 2>&1", ")", " ;", " && ", "`"):
        segment = segment.split(separator)[0]
    return segment.strip() or None


def _typer_walk(typer_instance: Any, path: list[str]) -> list[tuple[list[str], Any]]:
    """Yield ``(command path, CommandInfo)`` for every command in the app."""
    found: list[tuple[list[str], Any]] = []
    for command_info in typer_instance.registered_commands:
        name = command_info.name or command_info.callback.__name__.replace("_", "-")
        found.append((path + [name], command_info))
    for group in typer_instance.registered_groups:
        name = group.name or group.typer_instance.info.name
        found.extend(_typer_walk(group.typer_instance, path + [name]))
    return found


def documented_invocations() -> list[tuple[str, str]]:
    """Return ``(origin, invocation)`` for every documented command."""
    invocations: list[tuple[str, str]] = []
    for block in re.findall(r"```[a-zA-Z]*\n(.*?)```", README, re.S):
        for line in block.splitlines():
            invocation = _invocation_on_line(line.strip())
            if invocation:
                invocations.append(("README.md", invocation))
    for path, command_info in _typer_walk(app, []):
        for match in re.finditer(r"Example:\s*(torbox[^\n]*)", command_info.help or ""):
            invocations.append((" ".join(path) + " help", match.group(1).strip()))
    return invocations


def _skip_reason(invocation: str) -> str | None:
    for pattern, reason in EXECUTION_EXCLUSIONS.items():
        if pattern in invocation:
            return reason
    return None


INVOCATIONS = documented_invocations()
PARAMS = [
    pytest.param(
        origin,
        invocation,
        marks=(
            pytest.mark.skip(reason=_skip_reason(invocation))
            if _skip_reason(invocation)
            else ()
        ),
        id=f"{origin}: {invocation}",
    )
    for origin, invocation in INVOCATIONS
]


def test_the_sweep_covers_the_documented_surface() -> None:
    """Guard against an extractor that silently finds nothing."""
    assert len(INVOCATIONS) >= 100, (
        f"only found {len(INVOCATIONS)} documented invocations"
    )
    assert sum(1 for _, inv in INVOCATIONS if _skip_reason(inv)) <= 6


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
@pytest.mark.parametrize("origin,invocation", PARAMS)
def test_documented_invocation_parses(
    origin: str, invocation: str, tmp_path: Path, monkeypatch: Any, httpx_mock: Any
) -> None:
    monkeypatch.chdir(tmp_path)  # `--output` examples write relative paths
    httpx_mock.add_response(json={"success": True, "data": {}}, is_reusable=True)
    argv = shlex.split(invocation)[1:]
    result = runner.invoke(app, argv, env={"TORBOX_API_KEY": "dummy"}, input="yes\n")
    output = strip_ansi(result.output)
    for marker in PARSE_ERROR_MARKERS:
        assert marker not in output, (
            f"{origin} documents an invocation that does not parse: {invocation!r}\n"
            f"{output.strip()}"
        )


@pytest.mark.parametrize("invocation", RECIPES, ids=RECIPES)
def test_documented_recipes_run(
    invocation: str, tmp_path: Path, monkeypatch: Any, httpx_mock: Any
) -> None:
    """The cron/debug recipes and the previously broken examples must succeed."""
    monkeypatch.chdir(tmp_path)
    httpx_mock.add_response(json={"success": True, "data": {}}, is_reusable=True)
    argv = shlex.split(invocation)[1:]
    result = runner.invoke(app, argv, env={"TORBOX_API_KEY": "dummy"}, input="yes\n")
    assert result.exit_code == 0, f"{invocation!r} -> {strip_ansi(result.output)}"
