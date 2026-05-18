"""Allow python -m torbox to run the CLI."""

from __future__ import annotations

from torbox.cli import cli_entry

if __name__ == "__main__":
    cli_entry()
