#!/usr/bin/env python3
"""Helper script to generate a Homebrew formula for torbox-cli."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FORMULA_TEMPLATE = """\
class TorboxCli < Formula
  include Language::Python::Virtualenv

  desc "CLI wrapper for the TorBox API"
  homepage "https://github.com/remcov/torbox-cli"
  url "{URL}"
  sha256 "{SHA256}"
  license "MIT"

  depends_on "python@3.12"

  resource "typer" do
    url "https://files.pythonhosted.org/packages/source/t/typer/typer-0.25.1.tar.gz"
    sha256 "REPLACE_TYPER_SHA256"
  end

  # Additional resources should be generated with homebrew-pypi-poet

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"torbox", "--version"
  end
end
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Homebrew formula for torbox-cli"
    )
    parser.add_argument("--version", required=True, help="Package version (e.g. 1.0.0)")
    parser.add_argument("--sha256", required=True, help="SHA256 of the PyPI sdist")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to write formula (default: stdout)",
    )
    args = parser.parse_args()

    url = f"https://files.pythonhosted.org/packages/source/t/torbox-cli/torbox-cli-{args.version}.tar.gz"
    formula = FORMULA_TEMPLATE.format(
        VERSION=args.version,
        SHA256=args.sha256,
        URL=url,
    )

    if args.output:
        args.output.write_text(formula)
        print(f"Formula written to {args.output}", file=sys.stderr)
    else:
        print(formula)


if __name__ == "__main__":
    main()
