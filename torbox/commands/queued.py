"""Queued downloads commands: list, control."""

from __future__ import annotations

import builtins
from typing import Any

import typer
from typer import Context

from torbox.commands._helpers import (
    _get_client,
    _get_field,
    _is_quiet,
    _set_auto_retry,
    _should_json,
    confirm_destructive,
    dry_run_guard,
    handle_errors,
    print_json_envelope,
    validate_operation,
)
from torbox.formatters import print_panel, print_table

app = typer.Typer(help="Queued downloads management commands")


@app.command(
    help="GET /queued/getqueued — List queued downloads\n\nExample: torbox queued list"
)
@handle_errors
def list(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset"),
    limit: int = typer.Option(1000, "--limit", help="Pagination limit"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    params: dict[str, str | int] = {"offset": offset, "limit": limit}
    data: dict[str, Any] = client.get("/queued/getqueued", params=params)
    print_json_envelope(ctx, data, "queued list", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if isinstance(data.get("data"), builtins.list):
        if not _is_quiet(ctx):
            print_table(data["data"], "Queued")
    elif not _is_quiet(ctx):
        print_panel("No queued downloads found.", "Queued")


@app.command(
    help=(
        "POST /queued/addqueued — Add a download to the queue.\n\n"
        "Example: torbox queued add torrent 42"
    )
)
@handle_errors
def add(
    ctx: Context,
    type: str = typer.Argument(..., help="torrent | usenet | webdownload"),
    id: int = typer.Argument(..., help="Download ID to add to queue"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be sent without making the request"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    type = type.lower()
    if type not in {"torrent", "usenet", "webdownload"}:
        raise typer.BadParameter("type must be one of: torrent, usenet, webdownload")
    payload: dict[str, str | int] = {"type": type, "id": id}
    if dry_run_guard(
        ctx,
        "POST /queued/addqueued",
        payload=payload,
        dry_run=dry_run,
    ):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.post("/queued/addqueued", json=payload)
    print_json_envelope(ctx, data, "queued add", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel(f"Added {type} {id} to queue.", "Queued")


@app.command(
    help=(
        "POST /queued/controlqueued — Control queued item\n\n"
        "Example: torbox queued control 5 delete --yes"
    ),
)
@handle_errors
def control(
    ctx: Context,
    id: int,
    operation: str = typer.Argument(..., help="delete | pause | resume"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request without sending"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    operation = validate_operation(operation)
    if dry_run_guard(
        ctx,
        "POST /queued/controlqueued",
        {"queued_id": id, "operation": operation},
        dry_run=dry_run,
    ):
        return
    if not confirm_destructive(operation, "queued item", id, yes):
        raise typer.Exit(code=0)
    client = _get_client(ctx)
    data: dict[str, Any] = client.post(
        "/queued/controlqueued", json={"queued_id": id, "operation": operation}
    )
    print_json_envelope(ctx, data, "queued control", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel(f"Operation '{operation}' completed successfully.", f"Queued {id}")
