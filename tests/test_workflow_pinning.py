"""Workflow supply-chain guards (issue #43).

The workflows referenced actions by mutable major tags (`actions/checkout@v7`),
so a retagged or compromised action could change what this repository's CI runs
and — worse, because the release job holds `contents: write` — what its public
releases ship. The repository also had hash pinning unenforced and Dependabot
security updates off, so nothing kept the pins honest.

These are static checks on the committed files: every reference must be a full
commit sha carrying a `# vN` comment (so dependency tooling can move it), the CI
workflow must declare least-privilege permissions, and the Dependabot config
must cover GitHub Actions so the pins get maintained. The repository settings
(`sha_pinning_required`, security updates, branch protection) live on GitHub and
are verified there, not here.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
WORKFLOWS = sorted(WORKFLOW_DIR.glob("*.y*ml"))
DEPENDABOT = REPO_ROOT / ".github" / "dependabot.yml"
# A full git object name; a short sha or a tag is not immutable.
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def _action_references(workflow: Path) -> list[str]:
    return re.findall(r"^\s*-?\s*uses:\s*(\S+)", workflow.read_text(), re.MULTILINE)


def test_every_action_reference_is_pinned_to_a_commit() -> None:
    """A mutable tag can be retagged after review; a sha cannot."""
    assert WORKFLOWS, "no workflow files found"
    for workflow in WORKFLOWS:
        for ref in _action_references(workflow):
            if ref.startswith("./"):
                continue  # a local action is part of the reviewed checkout
            assert "@" in ref, f"{workflow.name}: {ref} has no ref"
            action, _, pin = ref.partition("@")
            assert FULL_SHA.match(pin), (
                f"{workflow.name}: {action} is pinned to '{pin}', not a full commit "
                "sha; resolve the tag with `gh api repos/<action>/commits/<tag>` and "
                "pin the commit (see issue #43)"
            )


def test_pinned_actions_record_their_version() -> None:
    """The `# vN` comment is what Dependabot uses to keep a pin current."""
    for workflow in WORKFLOWS:
        for line in workflow.read_text().splitlines():
            match = re.match(r"^\s*-?\s*uses:\s*(\S+@[0-9a-f]{40})\s*(.*)$", line)
            if match is None:
                continue
            assert re.search(r"#\s*v?\d", match.group(2)), (
                f"{workflow.name}: {match.group(1)} has no `# vN` comment, so an "
                "automated bump cannot tell which version the pin is (issue #43)"
            )


def test_ci_workflow_declares_least_privilege() -> None:
    """The test workflow only needs to read the repository."""
    text = (WORKFLOW_DIR / "ci.yml").read_text()
    match = re.search(r"^permissions:\n((?:\s+\S+:.*\n)+)", text, re.MULTILINE)
    assert match is not None, "ci.yml declares no top-level permissions block"
    assert "contents: read" in match.group(1), (
        "ci.yml must request read-only contents, or it inherits the repository "
        "default (see issue #43)"
    )
    assert "write" not in match.group(1)


def test_dependabot_maintains_the_action_pins() -> None:
    """Pinning without an update path is how pins rot."""
    config = DEPENDABOT.read_text()
    ecosystem = "package-ecosystem: github-actions"
    assert ecosystem in config.replace("'", "").replace('"', "")
