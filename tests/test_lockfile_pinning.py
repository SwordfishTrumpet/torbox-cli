"""Regression guard for the committed lockfile and its CI check.

Issue #36: ``uv.lock`` recorded the project's own VCS-derived version, so
``uv lock --check`` failed on every fresh checkout — including CI — and the
lint/type/test job never ran. Two invariants keep that from coming back:

1. The root project has no version in the lockfile: uv records it as
   ``(dynamic)`` because ``hatch-vcs`` derives the version from local git
   state, which can never match a fresh clone.
2. The workflows pin the uv version, so the lockfile revision and the uv that
   validates it cannot drift apart.

These are static file checks (no uv binary, no network), so the real guard —
``uv lock --check`` on a fresh clone — stays in CI where it belongs.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCKFILE = REPO_ROOT / "uv.lock"
# Every workflow, so a new one cannot quietly skip the uv pin.
WORKFLOWS = sorted((REPO_ROOT / ".github" / "workflows").glob("*.y*ml"))
# The lock revision this repository pins uv to. Bump both together: a lock
# written by a newer uv may use a revision the pinned uv cannot read.
LOCK_REVISION = 3


def _lockfile_package_block(name: str) -> str:
    """Return the ``[[package]]`` block whose ``name`` field matches ``name``."""
    text = LOCKFILE.read_text(encoding="utf-8")
    pattern = re.compile(rf'^name = "{re.escape(name)}"$', re.MULTILINE)
    blocks = [block for block in text.split("[[package]]") if pattern.search(block)]
    assert len(blocks) == 1, f"expected exactly one {name} entry, found {len(blocks)}"
    return blocks[0]


def _setup_uv_steps(workflow: Path) -> list[tuple[str, str]]:
    """Return ``(action ref, step body)`` for every setup-uv step in a workflow."""
    text = workflow.read_text(encoding="utf-8")
    steps: list[tuple[str, str]] = []
    for match in re.finditer(r"uses:\s*astral-sh/setup-uv@(\S+)", text):
        rest = text[match.end() :]
        boundary = re.search(r"^\s*- ", rest, re.MULTILINE)
        steps.append(
            (match.group(1), rest[: boundary.start() if boundary else len(rest)])
        )
    return steps


def test_lockfile_root_project_has_no_vcs_version() -> None:
    """A concrete self-version is derived from git state and breaks ``--check``."""
    block = _lockfile_package_block("torbox-cli")
    assert 'source = { editable = "." }' in block
    assert not re.search(r"^version = ", block, re.MULTILINE), (
        "uv.lock pins the VCS-derived project version; `uv lock --check` then "
        "fails on a fresh checkout (see issue #36). Regenerate the lock with a "
        "current uv so the root project is recorded as dynamic."
    )


def test_lockfile_uses_the_revisioned_dynamic_format() -> None:
    """The lock revision matches the uv version the workflows pin."""
    head = LOCKFILE.read_text(encoding="utf-8").split("[[package]]")[0]
    match = re.search(r"^revision = (\d+)$", head, re.MULTILINE)
    assert match is not None, "uv.lock has no revision field"
    assert int(match.group(1)) == LOCK_REVISION, (
        f"uv.lock is revision {int(match.group(1))}, but the workflows pin uv to "
        f"revision {LOCK_REVISION}; regenerate the lock with the pinned uv (or "
        "bump the pin, the lock, and LOCK_REVISION together)"
    )


def test_pyproject_declares_the_uv_floor() -> None:
    """A revision-3 lock needs uv >= 0.12, so the floor is machine-enforced."""
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^required-version\s*=\s*">=(\d+)\.(\d+)"', text, re.MULTILINE)
    assert match is not None, (
        "[tool.uv] required-version is missing, so a contributor on an old uv "
        "gets a cryptic lockfile error instead of an upgrade prompt"
    )
    floor = (int(match.group(1)), int(match.group(2)))
    assert floor >= (0, 12), f"required-version {floor} is below the lock's floor"


def test_workflows_pin_one_uv_version() -> None:
    """Every setup-uv step pins a version, and they all pin the same one."""
    pinned: list[str] = []
    workflows_with_uv = 0
    for workflow in WORKFLOWS:
        steps = _setup_uv_steps(workflow)
        if not steps:
            continue
        workflows_with_uv += 1
        for ref, body in steps:
            assert re.search(r"^\s+version:\s*\S", body, re.MULTILINE), (
                f"{workflow.name}: astral-sh/setup-uv@{ref} is unpinned, so the "
                "uv that validates uv.lock can change without the lock changing "
                "(see issue #36)"
            )
            match = re.search(r'^\s+version:\s*"?([0-9][^\s"\']*)', body, re.MULTILINE)
            assert match is not None, f"{workflow.name}: unreadable uv version pin"
            pinned.append(match.group(1))
    assert workflows_with_uv > 0, "no workflow sets up uv"
    assert len(set(pinned)) == 1, (
        f"workflows pin different uv versions {sorted(set(pinned))}; the lock "
        "writer and the lock checker must agree"
    )
