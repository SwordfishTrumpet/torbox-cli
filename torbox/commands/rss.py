"""RSS commands: list, items, create, edit, delete."""

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
)
from torbox.formatters import print_panel, print_table

app = typer.Typer(help="RSS feeds management commands")


@app.command(help="GET /rss/getfeeds — List RSS feeds. Example: torbox rss list")
@handle_errors
def list(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset"),
    limit: int = typer.Option(1000, "--limit", help="Pagination limit"),
    id: int | None = typer.Option(None, "--id", help="Specific feed ID"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    params: dict[str, str | int] = {"offset": offset, "limit": limit}
    if id is not None:
        params["id"] = id
    data: dict[str, Any] = client.get("/rss/getfeeds", params=params)
    print_json_envelope(ctx, data, "rss list", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if isinstance(data.get("data"), builtins.list):
        if not _is_quiet(ctx):
            print_table(data["data"], "RSS Feeds")
    elif not _is_quiet(ctx):
        print("RSS feeds: OK")


@app.command(
    help="GET /rss/getfeeditems — List items for a feed. Example: torbox rss items 1"
)
@handle_errors
def items(
    ctx: Context,
    feed_id: int,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    data: dict[str, Any] = client.get(f"/rss/getfeeditems?rss_feed_id={feed_id}")
    print_json_envelope(ctx, data, "rss items", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if isinstance(data.get("data"), builtins.list):
        if not _is_quiet(ctx):
            print_table(data["data"], f"RSS Items (feed {feed_id})")
    elif not _is_quiet(ctx):
        print(f"RSS items for feed {feed_id}: OK")


@app.command(
    help=(
        "POST /rss/addrss — Create RSS feed. "
        "Example: torbox rss create 'https://example.com/feed.xml' --name 'My Feed'"
    )
)
@handle_errors
def create(
    ctx: Context,
    url: str,
    name: str = typer.Option(..., "--name", help="Feed name (required)"),
    do_regex: str | None = typer.Option(
        None, "--do-regex", help="Regex to match items to download"
    ),
    dont_regex: str | None = typer.Option(
        None, "--dont-regex", help="Regex to exclude items"
    ),
    scan_interval: int | None = typer.Option(
        None, "--scan-interval", help="Scan interval in minutes"
    ),
    dont_older_than: int | None = typer.Option(
        None, "--dont-older-than", help="Skip items older than N days"
    ),
    rss_type: str | None = typer.Option(None, "--type", help="Feed type"),
    torrent_seeding: int | None = typer.Option(
        None, "--torrent-seeding", help="Torrent seeding option"
    ),
    pass_check: bool = typer.Option(False, "--pass-check", help="Pass check flag"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request payload and exit"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    payload: dict[str, str | int] = {"url": url, "name": name}
    if do_regex:
        payload["do_regex"] = do_regex
    if dont_regex:
        payload["dont_regex"] = dont_regex
    if scan_interval is not None:
        payload["scan_interval"] = scan_interval
    if dont_older_than is not None:
        payload["dont_older_than"] = dont_older_than
    if rss_type:
        payload["rss_type"] = rss_type
    if torrent_seeding is not None:
        payload["torrent_seeding"] = torrent_seeding
    if pass_check:
        payload["pass_check"] = True
    if dry_run_guard(ctx, "POST /rss/addrss", payload=payload, dry_run=dry_run):
        return
    data: dict[str, Any] = client.post("/rss/addrss", json=payload)
    print_json_envelope(ctx, data, "rss create", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    elif not _is_quiet(ctx):
        print_panel("RSS feed created successfully.", "Created")


@app.command(
    help=(
        "POST /rss/modifyrss — Edit RSS feed. "
        "Example: torbox rss edit 2 --name 'New Name'"
    )
)
@handle_errors
def edit(
    ctx: Context,
    id: int,
    name: str | None = typer.Option(None, "--name", help="Feed name"),
    do_regex: str | None = typer.Option(
        None, "--do-regex", help="Regex to match items to download"
    ),
    dont_regex: str | None = typer.Option(
        None, "--dont-regex", help="Regex to exclude items"
    ),
    scan_interval: int | None = typer.Option(
        None, "--scan-interval", help="Scan interval in minutes"
    ),
    dont_older_than: int | None = typer.Option(
        None, "--dont-older-than", help="Skip items older than N days"
    ),
    rss_type: str | None = typer.Option(None, "--type", help="Feed type"),
    torrent_seeding: int | None = typer.Option(
        None, "--torrent-seeding", help="Torrent seeding option"
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request payload and exit"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    payload: dict[str, str | int] = {"rss_feed_id": id}
    if name:
        payload["name"] = name
    if do_regex:
        payload["do_regex"] = do_regex
    if dont_regex:
        payload["dont_regex"] = dont_regex
    if scan_interval is not None:
        payload["scan_interval"] = scan_interval
    if dont_older_than is not None:
        payload["dont_older_than"] = dont_older_than
    if rss_type:
        payload["rss_type"] = rss_type
    if torrent_seeding is not None:
        payload["torrent_seeding"] = torrent_seeding
    if dry_run_guard(ctx, "POST /rss/modifyrss", payload=payload, dry_run=dry_run):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.post("/rss/modifyrss", json=payload)
    print_json_envelope(ctx, data, "rss edit", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    elif not _is_quiet(ctx):
        print_panel("RSS feed edited successfully.", f"RSS Feed {id}")


@app.command(
    help=("POST /rss/controlrss — Delete RSS feed. Example: torbox rss delete 2 --yes")
)
@handle_errors
def delete(
    ctx: Context,
    id: int,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request payload and exit"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    payload: dict[str, str | int] = {"rss_feed_id": id, "operation": "delete"}
    if dry_run_guard(ctx, "POST /rss/controlrss", payload=payload, dry_run=dry_run):
        return
    if not confirm_destructive("delete", "RSS feed", id, yes):
        raise typer.Exit(code=0)
    client = _get_client(ctx)
    data: dict[str, Any] = client.post("/rss/controlrss", json=payload)
    print_json_envelope(ctx, data, "rss delete", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    elif not _is_quiet(ctx):
        print_panel("RSS feed deleted successfully.", f"RSS Feed {id}")
