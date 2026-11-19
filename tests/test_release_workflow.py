"""The release job must run the artifact it ships, before it ships it (#65).

``uv build`` plus an asset-name check proved nothing about whether the wheel
starts, so a revision that CI's smoke test would reject could be published and
become ``releases/latest``. The workflow now installs and runs the built wheel
before the publish step, and deletes the release it created when the asset
check fails. The executable proof is the audited reproduction replayed by hand
(a renamed console-script target must stop the job before upload); this is the
cheap structural guard against deleting those steps.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"


def _text() -> str:
    return RELEASE_WORKFLOW.read_text(encoding="utf-8")


def test_the_wheel_is_installed_and_run_before_the_release_is_created() -> None:
    text = _text()
    publish_at = text.index("action-gh-release")
    before = text[:publish_at]
    assert "dist/torbox_cli-*.whl" in before, (
        "release.yml publishes without installing the wheel it builds, so a "
        "wheel whose console script cannot start ships green (issue #65)"
    )
    assert "torbox --version" in before, (
        "release.yml installs the wheel but never runs it, so a broken "
        "console entry point is still published (issue #65)"
    )


def test_a_failed_asset_check_deletes_the_release() -> None:
    text = _text()
    check_at = text.index("scripts/check_release_assets.sh")
    after = text[check_at:]
    assert "gh release delete" in after, (
        "a failed asset check leaves the release page live (issue #65)"
    )
