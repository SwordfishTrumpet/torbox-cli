"""Main Typer CLI app for TorBox."""

from __future__ import annotations

import signal
import sys
from pathlib import Path
from typing import Any

import typer
from typer import Context

import torbox
from torbox.commands import (
    config_cmd,
    general,
    integrations,
    notifications,
    queued,
    rss,
    search,
    stream,
    torrents,
    usenet,
    user,
    webdl,
)
from torbox.exceptions import TorBoxError
from torbox.formatters import print_error_json, print_human_error

app = typer.Typer(
    help=(
        "TorBox CLI — wrapper for TorBox API v1. "
        "Full --json/-j and --field/-f support for LLM/automation use. "
        "All list/info use rich formatters in human mode. "
        "Exit codes: 0=ok,1=general,2=auth,3=api/err,4=ratelimit,5=plan,6=notfound,"
        "130=interrupted."
    ),
    invoke_without_command=True,
)


def _handle_interrupt(signum: int, frame: Any) -> None:
    """Handle Ctrl-C gracefully with exit code 130."""
    sys.exit(130)


signal.signal(signal.SIGINT, _handle_interrupt)


def _print_error_json(exc: TorBoxError) -> None:
    """Print a JSON error payload including the exit_code."""
    print_error_json(exc)


@app.callback()
def cli_callback(
    ctx: Context,
    api_key: str | None = typer.Option(
        None, "--api-key", "-k", help="Override API key from config/env"
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="Output raw API JSON (primary for agents/LLMs)"
    ),
    field: str | None = typer.Option(
        None, "--field", "-f", help="Dot-path extract e.g. data.0.name or success"
    ),
    config: Path | None = typer.Option(
        None, "--config", help="Path to custom config/env file"
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help=("Profile name from INI-style config file (e.g. [work] section)"),
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential human-mode output"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose request diagnostics to stderr"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
    compact: bool = typer.Option(
        False, "--compact", help="Compact single-line JSON (no whitespace)"
    ),
    version: bool = typer.Option(
        False, "--version", help="Show version and exit", is_eager=True
    ),
) -> None:
    """TorBox CLI entry. Global flags apply to all subcommands.
    --json enables machine mode; human uses formatters.
    """
    if version:
        print(torbox.__version__)
        raise typer.Exit()
    ctx.obj = {
        "json": json_output,
        "field": field,
        "api_key": api_key,
        "config": str(config) if config else None,
        "profile": profile,
        "quiet": quiet,
        "verbose": verbose,
        "auto_retry": auto_retry,
        "compact": compact,
    }


@app.command(help="Generate man page for the CLI")
def docs(
    ctx: Context,
    man: bool = typer.Option(False, "--man", help="Output troff man page"),
) -> None:
    """Generate documentation. Use --man for troff output."""
    if man:
        print(".TH TORBOX 1")
        print(".SH NAME")
        print("torbox \\- TorBox CLI")
    else:
        print("Use --man for man page output")


app.add_typer(
    config_cmd.app,
    name="config",
    help="Configuration inspection — doctor, resolution order, effective values",
)
app.add_typer(
    general.app,
    name="general",
    help="General endpoints (no auth) — status, stats, changelogs, speedtest",
)
app.add_typer(
    user.app,
    name="user",
    help="User account, settings, transactions, search engines, auth flows",
)
app.add_typer(
    torrents.app,
    name="torrents",
    help=(
        "Torrent management: list, info, create, control, "
        "checkcached, requestdl, export"
    ),
)
app.add_typer(
    usenet.app,
    name="usenet",
    help="Usenet management: list, create, control, requestdl",
)
app.add_typer(
    webdl.app, name="webdl", help="Web downloads: list, create, control, edit, hosters"
)
app.add_typer(
    rss.app, name="rss", help="RSS: list feeds, items, create/edit/delete feeds"
)
app.add_typer(queued.app, name="queued", help="Queued downloads management and control")
app.add_typer(
    stream.app, name="stream", help="Create streams and fetch stream data for video"
)
app.add_typer(
    notifications.app,
    name="notifications",
    help="Notifications management — list, rss, test, clear",
)
app.add_typer(
    integrations.app,
    name="integrations",
    help="Integrations management — cloud upload jobs (jobs, cancel)",
)
app.add_typer(
    search.app,
    name="search",
    help="Search torrent streams and library [Unofficial — Stremio addon]",
)


def cli_entry() -> None:
    """Entry point with unified exception handling."""
    try:
        app()
    except TorBoxError as exc:
        if any(arg in sys.argv for arg in ("--json", "-j")):
            _print_error_json(exc)
        else:
            verbose = any(arg in sys.argv for arg in ("--verbose", "-v"))
            print_human_error(exc, verbose=verbose)
        sys.exit(exc.exit_code)


if __name__ == "__main__":
    cli_entry()
