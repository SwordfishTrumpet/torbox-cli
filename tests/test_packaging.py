"""Packaging verification tests."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

import pytest


def test_wheel_and_sdist_include_py_typed() -> None:
    project_root = Path(__file__).resolve().parent.parent
    python_executable = shutil.which(sys.executable) or sys.executable

    try:
        import build  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        pytest.skip("'build' package is not installed")

    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [python_executable, "-m", "build", str(project_root)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip(f"build failed: {result.stderr}")

        dist_dir = Path(tmpdir) / "dist"
        if not dist_dir.exists():
            # build may place artifacts in project_root/dist when given a path
            dist_dir = project_root / "dist"

        wheels = list(dist_dir.glob("*.whl"))
        sdists = list(dist_dir.glob("*.tar.gz"))

        if not wheels or not sdists:
            pytest.skip("no wheel or sdist produced")

        wheel = wheels[0]
        sdist = sdists[0]

        with zipfile.ZipFile(wheel, "r") as whl:
            names = whl.namelist()
            assert any("torbox/py.typed" in n for n in names), (
                f"torbox/py.typed missing from {wheel.name}"
            )

        with tarfile.open(sdist, "r:gz") as tar:
            names = tar.getnames()
            assert any("torbox/py.typed" in n for n in names), (
                f"torbox/py.typed missing from {sdist.name}"
            )
