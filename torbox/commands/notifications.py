"""Notifications commands: list, rss, test, clear."""

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
    dry_run_guard,
    handle_errors,
    print_json_envelope,
)
from torbox.formatters import print_panel, print_table

app = typer.Typer(help="Notifications management")


@app.command(
    help=(
        "GET /notifications/mynotifications — List all notifications. "
        "Example: torbox notifications list"
    )
)
@handle_errors
def list(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    data: dict[str, Any] = client.get("/notifications/mynotifications")
    print_json_envelope(ctx, data, "notifications list", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if isinstance(data.get("data"), builtins.list):
        if not _is_quiet(ctx):
            print_table(data["data"], "Notifications")
    elif not _is_quiet(ctx):
        print_panel("Notifications list retrieved.", "Notifications")


@app.command(
    help=(
        "GET /notifications/rss — Get RSS feed of notifications. "
        "Example: torbox notifications rss"
    )
)
@handle_errors
def rss(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    resp = client.get_bytes("/notifications/rss", params={"token": client.api_key})
    raw_text = resp.text
    print_json_envelope(ctx, raw_text, "notifications rss", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print(raw_text)


@app.command(
    help=(
        "POST /notifications/test — Send a test notification. "
        "Example: torbox notifications test"
    )
)
@handle_errors
def test(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    data: dict[str, Any] = client.post("/notifications/test")
    print_json_envelope(ctx, data, "notifications test", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("Test notification sent successfully.", "Test Sent")


@app.command(
    help=(
        "POST /notifications/clear — Clear all notifications. "
        "Example: torbox notifications clear --yes"
    )
)
@handle_errors
def clear(
    ctx: Context,
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
    if dry_run_guard(ctx, "POST /notifications/clear", payload={}, dry_run=dry_run):
        return
    if not yes:
        prompt = "Are you sure you want to clear ALL notifications? [y/N]: "
        answer = input(prompt).strip().lower()
        if answer not in {"y", "yes"}:
            raise typer.Exit(code=0)
    client = _get_client(ctx)
    data: dict[str, Any] = client.post("/notifications/clear")
    print_json_envelope(ctx, data, "notifications clear", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("All notifications cleared successfully.", "Cleared")
