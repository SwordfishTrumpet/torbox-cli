"""Integrations commands: jobs, cancel."""

from __future__ import annotations

from typing import Any

import typer
from typer import Context

from torbox.commands._helpers import (
    _get_client,
    _get_field,
    _is_quiet,
    _should_json,
    dry_run_guard,
    handle_errors,
    print_json_envelope,
)
from torbox.formatters import print_dict_panel, print_panel, print_table

app = typer.Typer(help="Integrations management — cloud upload jobs")


@app.command(
    help=(
        "GET /integration/jobs/{hash} — Get integration jobs for a download hash\n\n"
        "Example: torbox integrations jobs abc123def456"
    )
)
@handle_errors
def jobs(
    ctx: Context,
    hash: str,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
) -> None:
    client = _get_client(ctx)
    data: dict[str, Any] = client.get(f"/integration/jobs/{hash}")
    print_json_envelope(ctx, data, "integrations jobs", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if isinstance(data.get("data"), list):
        if not _is_quiet(ctx):
            print_table(data["data"], "Integration Jobs")
    elif not _is_quiet(ctx):
        print_dict_panel(data.get("data", {}), f"Integration Jobs for {hash}")


@app.command(
    help=(
        "DELETE /integration/job/{job_id} — Cancel an integration job\n\n"
        "Example: torbox integrations cancel job_abc123 --yes"
    )
)
@handle_errors
def cancel(
    ctx: Context,
    job_id: str,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request without sending"
    ),
) -> None:
    if dry_run_guard(
        ctx,
        f"DELETE /integration/job/{job_id}",
        payload={"job_id": job_id},
        dry_run=dry_run,
    ):
        return
    if not yes:
        answer = (
            input(f"Are you sure you want to cancel integration job {job_id}? [y/N]: ")
            .strip()
            .lower()
        )
        if answer not in {"y", "yes"}:
            raise typer.Exit(code=0)
    client = _get_client(ctx)
    data: dict[str, Any] = client.delete(f"/integration/job/{job_id}")
    print_json_envelope(ctx, data, "integrations cancel", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("Integration job cancelled.", f"Job {job_id}")
