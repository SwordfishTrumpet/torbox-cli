"""Consistency guards for the release-facing documents (issue #44).

The disclaimer described a `search` command group and its Cinemeta/Stremio data
flows that had been deleted a release earlier, the changelog never recorded the
removal, its unreleased link compared from a tag two releases behind, and the
packaging metadata pointed at a branch this repository does not have. Every one
of those was a manual step with no check, so this module turns the mechanical
parts of "the release documents describe the shipped tool" into assertions:

1. Every ``## [x.y.z]`` changelog heading has a matching ``[x.y.z]:`` link
   definition, so a new release section cannot render as literal text.
2. The ``[unreleased]`` link compares from the newest release heading, so the
   diff link follows the latest release instead of the release history start.
3. The metadata changelog URL names the default branch, read from the CI
   workflow's push trigger rather than hardcoded here.

Whether the referenced tags actually exist needs the network and is checked by
opening the links, not by this suite (tests/conftest.py blocks network calls).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
PYPROJECT = REPO_ROOT / "pyproject.toml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _changelog_text() -> str:
    return CHANGELOG.read_text(encoding="utf-8")


def _release_headings() -> list[str]:
    """Return release versions in file order (newest first), excluding Unreleased."""
    return re.findall(r"^## \[(\d+\.\d+\.\d+)\]", _changelog_text(), re.MULTILINE)


def _link_definitions() -> dict[str, str]:
    """Return the changelog's ``[name]: url`` reference definitions."""
    return dict(re.findall(r"^\[([^\]]+)\]: (\S+)", _changelog_text(), re.MULTILINE))


def _default_branch() -> str:
    """The default branch as declared by the CI workflow's push trigger."""
    match = re.search(
        r"^on:\n(?:.*\n)*?\s+push:\n\s+branches:\s*\[([^\]]+)\]",
        CI_WORKFLOW.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert match is not None, "ci.yml no longer declares a push branch trigger"
    return match.group(1).split(",")[0].strip().strip("\"'")


def test_every_release_heading_has_a_link_definition() -> None:
    """A missing definition renders the heading as literal ``[1.2.0]``."""
    definitions = _link_definitions()
    for version in _release_headings():
        assert version in definitions, (
            f"CHANGELOG.md has a `## [{version}]` section with no `[{version}]:` "
            "link definition, so the newest release entries render as plain text "
            "(see issue #44)"
        )


def test_unreleased_link_compares_from_the_newest_release() -> None:
    """The unreleased diff link must start at the latest released tag."""
    newest = _release_headings()[0]
    url = _link_definitions()["unreleased"]
    assert f"compare/v{newest}...HEAD" in url, (
        f"[unreleased] compares from {url}, not the newest release v{newest}; "
        "the diff link then shows every release since the stale base (issue #44)"
    )


def test_metadata_changelog_url_uses_the_default_branch() -> None:
    """`main` was configured as the changelog branch; the default is `master`."""
    match = re.search(
        r'^Changelog\s*=\s*"([^"]+)"', PYPROJECT.read_text(), re.MULTILINE
    )
    assert match is not None, "pyproject.toml has no Changelog project url"
    branch = _default_branch()
    assert f"/blob/{branch}/" in match.group(1), (
        f"the metadata changelog url points at {match.group(1)}, which does not "
        f"resolve: this repository's default branch is {branch} (see issue #44)"
    )
