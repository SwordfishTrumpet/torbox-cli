"""Regression tests for the repository ignore rules (issue #48).

The release step stages every change (`git add -A`), so any local-only runtime
state at the repository root must be ignored or it ships with the release.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Pipeline runtime state plus the planning documents that were already ignored.
LOCAL_ONLY = [
    "LEDGER.tsv",
    ".pipeline-lock",
    "TODO.md",
    "AGENTS.md",
    "TRD.md",
]


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )


@pytest.fixture(scope="module", autouse=True)
def _require_git() -> None:
    if shutil.which("git") is None or _git("rev-parse", "--git-dir").returncode != 0:
        pytest.skip("not a git checkout")


@pytest.mark.parametrize("path", LOCAL_ONLY)
def test_local_only_path_is_ignored(path: str) -> None:
    assert _git("check-ignore", "-q", path).returncode == 0, f"{path} is not ignored"


def test_blanket_stage_does_not_add_runtime_state() -> None:
    """`git add -A --dry-run` must not stage the ledger or a held lock."""
    out = _git("add", "-A", "--dry-run").stdout
    assert "LEDGER.tsv" not in out
    assert ".pipeline-lock" not in out
