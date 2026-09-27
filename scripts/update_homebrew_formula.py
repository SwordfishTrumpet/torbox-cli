#!/usr/bin/env python3
"""Generate a Homebrew formula for torbox-cli.

The formula downloads the sdist from GitHub Releases. Two things made earlier
output unusable:

* The url was built from the PyPI-style hyphenated name (``torbox-cli-1.3.1.tar.gz``)
  while releases publish the normalized underscore name (``torbox_cli-1.3.1.tar.gz``),
  so the download 404d.
* Only ``typer`` was declared as a resource, with a placeholder checksum, so the
  resulting formula installed an environment the CLI cannot run in.

The url now comes from the published artifact name, the checksum is either given
with ``--sha256`` or computed by downloading the asset, and the resource blocks
are generated from the committed lockfile via PyPI metadata, which gives the full
transitive closure rather than only the direct dependencies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import IO, Any

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECT = "SwordfishTrumpet/torbox-cli"
RELEASE_BASE_URL = f"https://github.com/{PROJECT}/releases/download"
PYPI_JSON_URL = "https://pypi.org/pypi/{name}/{version}/json"
LOCKFILE = REPO_ROOT / "uv.lock"
DEFAULT_PYTHON = "3.12"

FORMULA_TEMPLATE = """\
class TorboxCli < Formula
  include Language::Python::Virtualenv

  desc "CLI wrapper for the TorBox API"
  homepage "https://github.com/{project}"
  url "{url}"
  sha256 "{sha256}"
  license "MIT"

  depends_on "python@{python}"

{resources}
  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"torbox", "--version"
  end
end
"""

RESOURCE_TEMPLATE = """\
  resource "{name}" do
    url "{url}"
    sha256 "{sha256}"
  end
"""


def sdist_filename(version: str) -> str:
    """The release artifact name, normalized to underscores by the build backend."""
    return f"torbox_cli-{version}.tar.gz"


def sdist_url(version: str) -> str:
    """Absolute url of the sdist attached to the ``v{version}`` release."""
    return f"{RELEASE_BASE_URL}/v{version}/{sdist_filename(version)}"


def _open(url: str) -> IO[bytes]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "torbox-cli-homebrew-helper"}
    )
    return urllib.request.urlopen(request, timeout=60)  # noqa: S310 - https literals


def fetch_json(url: str) -> dict[str, Any]:
    """Fetch and decode a JSON document. Replaced in tests."""
    with _open(url) as response:
        return json.load(response)  # type: ignore[no-any-return]


def sha256_of_url(url: str) -> str:
    """Stream a url and return the hex sha256 of its bytes.

    Also the check that the url exists: a missing release asset fails here rather
    than in the generated formula.
    """
    digest = hashlib.sha256()
    with _open(url) as response:
        for chunk in iter(lambda: response.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _version_key(version: str) -> tuple[int, ...]:
    parts = re.split(r"[.\-+]", version)
    return tuple(int(part) if part.isdigit() else 0 for part in parts)


def parse_locked_packages(lock_text: str) -> list[tuple[str, str]]:
    """Return ``(name, version)`` for every locked package, newest version per name.

    The root project is skipped (it is the formula's subject, not a resource) and
    a dependency locked at several versions for different resolution markers
    collapses to its highest version, which is the one that applies to the
    formula's ``python@`` dependency.
    """
    found: dict[str, str] = {}
    for block in lock_text.split("[[package]]")[1:]:
        if 'source = { editable = "." }' in block:
            continue
        name = re.search(r'^name = "([^"]+)"', block, re.MULTILINE)
        version = re.search(r'^version = "([^"]+)"', block, re.MULTILINE)
        if name is None or version is None:
            continue
        existing = found.get(name.group(1))
        if existing is None or _version_key(version.group(1)) > _version_key(existing):
            found[name.group(1)] = version.group(1)
    return sorted(found.items())


def resource_for(name: str, version: str) -> tuple[str, str]:
    """Return ``(url, sha256)`` of a package's sdist, from PyPI metadata."""
    metadata = fetch_json(PYPI_JSON_URL.format(name=name, version=version))
    for file_info in metadata.get("urls") or []:
        if file_info.get("packagetype") == "sdist":
            return str(file_info["url"]), str(file_info["digests"]["sha256"])
    raise SystemExit(f"error: no sdist published for {name} {version}")


def render_formula(
    version: str,
    checksum: str,
    resources: list[tuple[str, str, str]],
    python: str = DEFAULT_PYTHON,
) -> str:
    """Render the formula text for a release."""
    resource_blocks = "\n".join(
        RESOURCE_TEMPLATE.format(name=name, url=url, sha256=sha)
        for name, url, sha in sorted(resources)
    )
    return FORMULA_TEMPLATE.format(
        project=PROJECT,
        url=sdist_url(version),
        sha256=checksum,
        python=python,
        resources=resource_blocks,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Homebrew formula for torbox-cli",
        epilog=(
            "The sdist is published as torbox_cli-<version>.tar.gz; when --sha256 "
            "is omitted the asset is downloaded so its checksum is real and its "
            "url is known to exist."
        ),
    )
    parser.add_argument("--version", required=True, help="Package version (e.g. 1.3.1)")
    parser.add_argument(
        "--sha256",
        default=None,
        help="SHA256 of the release sdist (default: download the asset and compute it)",
    )
    parser.add_argument(
        "--lock",
        type=Path,
        default=LOCKFILE,
        help=f"Lockfile the resource list is generated from (default: {LOCKFILE.name})",
    )
    parser.add_argument(
        "--python",
        default=DEFAULT_PYTHON,
        help=f"Homebrew python formula version (default: {DEFAULT_PYTHON})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to write formula (default: stdout)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    url = sdist_url(args.version)
    checksum = args.sha256 or sha256_of_url(url)
    locked = parse_locked_packages(args.lock.read_text(encoding="utf-8"))
    if not locked:
        print(f"error: no packages found in {args.lock}", file=sys.stderr)
        return 1
    resources = []
    for name, version in locked:
        resource_url, resource_sha = resource_for(name, version)
        resources.append((name, resource_url, resource_sha))
    formula = render_formula(args.version, checksum, resources, args.python)

    if args.output:
        args.output.write_text(formula, encoding="utf-8")
        print(f"Formula written to {args.output}", file=sys.stderr)
    else:
        print(formula)
    return 0


if __name__ == "__main__":
    sys.exit(main())
