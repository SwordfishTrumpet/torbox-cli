"""Tests for the Homebrew formula helper (issue #41).

The helper generated a formula whose url used the hyphenated PyPI name (releases
publish ``torbox_cli-<version>.tar.gz``) and declared a single resource with a
placeholder checksum. These tests pin the artifact name, the checksum source and
the resource generation, driving the real script against the real committed
lockfile with the network replaced by fakes.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "update_homebrew_formula.py"
LOCKFILE = REPO_ROOT / "uv.lock"
# The runtime dependencies the formula must install for `torbox` to run.
RUNTIME_DEPENDENCIES = {"typer", "httpx", "rich", "python-dotenv", "click"}


def _load_helper() -> Any:
    spec = importlib.util.spec_from_file_location("update_homebrew_formula", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helper = _load_helper()


def _fake_pypi_metadata(name: str, version: str, url: str) -> dict[str, Any]:
    return {
        "info": {"name": name, "version": version},
        "urls": [
            {
                "packagetype": "bdist_wheel",
                "url": f"https://files.example/{name}-{version}-py3-none-any.whl",
                "digests": {"sha256": "b" * 64},
            },
            {
                "packagetype": "sdist",
                "url": f"https://files.example/{name}-{version}.tar.gz",
                "digests": {"sha256": "a" * 64},
            },
        ],
    }


@pytest.fixture()
def offline(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Replace the network with fakes that record what was requested."""
    calls: dict[str, Any] = {"pypi": [], "downloaded": []}

    def fake_fetch_json(url: str) -> dict[str, Any]:
        match = re.search(r"/pypi/([^/]+)/([^/]+)/json", url)
        assert match is not None, url
        name, version = match.group(1), match.group(2)
        calls["pypi"].append((name, version))
        return _fake_pypi_metadata(name, version, url)

    def fake_sha256_of_url(url: str) -> str:
        calls["downloaded"].append(url)
        return hashlib.sha256(b"release-asset").hexdigest()

    monkeypatch.setattr(helper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(helper, "sha256_of_url", fake_sha256_of_url)
    return calls


def test_sdist_url_uses_the_published_artifact_name() -> None:
    """Releases publish the underscore name; the hyphenated one 404s."""
    url = helper.sdist_url("1.3.1")
    assert url.endswith("/v1.3.1/torbox_cli-1.3.1.tar.gz")
    assert url.startswith(
        "https://github.com/SwordfishTrumpet/torbox-cli/releases/download/"
    )
    assert "torbox-cli-1.3.1.tar.gz" not in url


def test_parse_locked_packages_skips_the_project_and_keeps_newest() -> None:
    """The root project is not a resource, and marker duplicates collapse."""
    lock_text = """
[[package]]
name = "torbox-cli"
source = { editable = "." }

[[package]]
name = "typing-extensions"
version = "4.15.0"

[[package]]
name = "typing-extensions"
version = "4.16.0"

[[package]]
name = "click"
version = "8.4.1"
"""
    assert helper.parse_locked_packages(lock_text) == [
        ("click", "8.4.1"),
        ("typing-extensions", "4.16.0"),
    ]


def test_resource_for_prefers_the_sdist(monkeypatch: pytest.MonkeyPatch) -> None:
    """A resource points at the sdist, whose digest is published by PyPI."""
    monkeypatch.setattr(
        helper,
        "fetch_json",
        lambda url: _fake_pypi_metadata("typer", "0.26.7", url),
    )
    url, sha = helper.resource_for("typer", "0.26.7")
    assert url == "https://files.example/typer-0.26.7.tar.gz"
    assert sha == "a" * 64


def test_checksum_is_computed_from_the_downloaded_asset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without --sha256 the asset is fetched, which also proves the url exists."""
    payload = b"torbox_cli sdist bytes"
    monkeypatch.setattr(helper, "_open", lambda url: io.BytesIO(payload))
    assert (
        helper.sha256_of_url("https://example/torbox_cli-1.3.1.tar.gz")
        == hashlib.sha256(payload).hexdigest()
    )


def test_formula_covers_every_locked_package(
    offline: dict[str, Any], tmp_path: Path
) -> None:
    """The real lockfile drives the resource list; nothing is hand-maintained."""
    output = tmp_path / "torbox-cli.rb"
    exit_code = helper.main(
        ["--version", "1.3.1", "--lock", str(LOCKFILE), "--output", str(output)]
    )
    assert exit_code == 0

    formula = output.read_text(encoding="utf-8")
    resources = set(re.findall(r'^  resource "([^"]+)" do$', formula, re.MULTILINE))
    assert RUNTIME_DEPENDENCIES <= resources, (
        "formula installs an incomplete environment; missing "
        f"{RUNTIME_DEPENDENCIES - resources}"
    )
    assert "REPLACE_" not in formula and "placeholder" not in formula

    # Every locked package is requested from PyPI, and the project itself is not.
    requested = {name for name, _ in offline["pypi"]}
    assert RUNTIME_DEPENDENCIES <= requested
    assert "torbox-cli" not in requested
    assert len(resources) == len(requested)

    # The url is the real published artifact and its checksum came from the asset.
    assert (
        'url "https://github.com/SwordfishTrumpet/torbox-cli/releases/download/'
        in formula
    )
    assert "torbox_cli-1.3.1.tar.gz" in formula
    assert hashlib.sha256(b"release-asset").hexdigest() in formula
    assert offline["downloaded"] == [helper.sdist_url("1.3.1")]
    assert 'depends_on "python@3.12"' in formula
    assert "virtualenv_install_with_resources" in formula


def test_explicit_sha256_skips_the_download(
    offline: dict[str, Any], tmp_path: Path
) -> None:
    """A supplied checksum is used as given, without a network round trip."""
    output = tmp_path / "torbox-cli.rb"
    helper.main(
        [
            "--version",
            "1.3.1",
            "--sha256",
            "c" * 64,
            "--lock",
            str(LOCKFILE),
            "--output",
            str(output),
        ]
    )
    formula = output.read_text(encoding="utf-8")
    assert f'sha256 "{"c" * 64}"' in formula
    assert offline["downloaded"] == []


def test_missing_sdist_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    """A package published without an sdist fails loudly, not with a broken formula."""
    monkeypatch.setattr(
        helper,
        "fetch_json",
        lambda url: {
            "urls": [{"packagetype": "bdist_wheel", "url": "u", "digests": {}}]
        },
    )
    with pytest.raises(SystemExit, match="no sdist published for typer"):
        helper.resource_for("typer", "0.26.7")
