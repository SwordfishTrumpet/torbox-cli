"""The release must carry exactly the built artifacts (issue #53).

``uv build`` seeds ``dist/`` with a ``.gitignore``, the release workflow uploaded
the whole directory, and every release page then offered a ``default.gitignore``
download next to the wheel, the source archive and ``requirements.lock.txt``.

The workflow now removes the dotfile before uploading and runs the committed
``scripts/check_release_assets.sh`` against the published release. These tests
run that script with a stubbed ``gh`` so the exact-asset rule is exercised, not
just asserted present in YAML, and check the workflow still wires it up.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"
CHECK_SCRIPT = REPO_ROOT / "scripts" / "check_release_assets.sh"

# What the release job builds, in the sorted order `gh --jq 'sort'` reports:
# the wheel, the sdist and the exported lock list.
WHEEL = "torbox_cli-1.0.0-py3-none-any.whl"
SDIST = "torbox_cli-1.0.0.tar.gz"
REQUIREMENTS = "requirements.lock.txt"
GOOD_ASSETS = f"{REQUIREMENTS},{WHEEL},{SDIST}"


def _run_check(tmp_path: Path, assets: str) -> subprocess.CompletedProcess[str]:
    """Run the real check script with a stub ``gh`` that reports ``assets``."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "gh"
    stub.write_text(f'#!/bin/sh\nprintf %s "{assets}"\n', encoding="utf-8")
    stub.chmod(0o755)

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "torbox_cli-1.0.0-py3-none-any.whl").write_text("", encoding="utf-8")
    (dist / "torbox_cli-1.0.0.tar.gz").write_text("", encoding="utf-8")
    (tmp_path / "requirements.lock.txt").write_text("", encoding="utf-8")

    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        ["bash", str(CHECK_SCRIPT), "v1.0.0"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )


def test_check_accepts_the_exact_asset_set(tmp_path: Path) -> None:
    result = _run_check(tmp_path, GOOD_ASSETS)
    assert result.returncode == 0, result.stderr


def test_check_rejects_an_unexpected_asset(tmp_path: Path) -> None:
    """The default.gitignore the build writes must fail the release job."""
    result = _run_check(tmp_path, f"default.gitignore,{GOOD_ASSETS}")
    assert result.returncode == 1
    assert "default.gitignore" in result.stderr


def test_check_rejects_a_missing_asset(tmp_path: Path) -> None:
    result = _run_check(tmp_path, f"{REQUIREMENTS},{WHEEL}")
    assert result.returncode == 1


def test_workflow_removes_the_build_dotfile_before_upload() -> None:
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "rm -f dist/.gitignore" in text, (
        "release.yml uploads dist/* without removing the .gitignore uv build "
        "writes, so the release page offers a non-artifact (issue #53)"
    )


def test_workflow_runs_the_asset_check() -> None:
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "scripts/check_release_assets.sh" in text, (
        "release.yml no longer verifies the published asset set, so an "
        "unexpected asset can ship unnoticed (issue #53)"
    )
