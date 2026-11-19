"""One command runs the same checks CI runs (#86).

The pipeline's quality gate reads its check commands from a manifest it can
parse (``package.json`` scripts or a Makefile target). Without one it reported
``GATE GAP`` and could never go green, so an automated change could merge with
the suite never executed. ``package.json`` now names the four checks, and this
test keeps them equal to what ``.github/workflows/ci.yml`` runs, so the local
command and the CI command cannot drift apart.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_JSON = REPO_ROOT / "package.json"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

# The four steps the CI lint/type/test job runs, by the substring that names
# them. `pytest` is listed without flags because CI adds coverage reporting.
CHECK_COMMANDS = (
    "ruff check .",
    "ruff format --check .",
    "mypy --strict torbox",
    "pytest",
)


def _scripts() -> dict[str, str]:
    return json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))["scripts"]


def test_the_task_runner_names_every_check() -> None:
    scripts = _scripts()
    for key in ("lint", "typecheck", "test", "check"):
        assert key in scripts, f"package.json has no {key!r} script"


def test_each_ci_check_is_reachable_from_one_script() -> None:
    scripts = _scripts()
    joined = "\n".join(scripts.values())
    for command in CHECK_COMMANDS:
        assert command in joined, f"no package.json script runs {command!r}"


def test_ci_and_the_local_entry_point_run_the_same_checks() -> None:
    ci_text = CI_WORKFLOW.read_text(encoding="utf-8")
    scripts = "\n".join(_scripts().values())
    for command in CHECK_COMMANDS:
        assert command in ci_text, (
            f"{command!r} is in package.json but not in ci.yml (or the wording "
            "changed), so the local entry point no longer matches CI (#86)"
        )
        assert command in scripts, (
            f"{command!r} runs in ci.yml but not from package.json, so "
            "`npm run check` no longer matches CI (#86)"
        )


def test_check_script_aggregates_the_other_three() -> None:
    check = _scripts()["check"]
    assert "lint" in check and "typecheck" in check and "test" in check
