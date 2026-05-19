"""Web downloads commands: list, create, control, edit, hosters."""

from __future__ import annotations

import builtins
from typing import Any

import typer
from typer import Context

from torbox.commands._helpers import (
    _get_client,
    _get_field,
    _is_quiet,
    _should_json,
    confirm_bulk_destructive,
    confirm_destructive,
    dry_run_guard,
    handle_errors,
    print_json_envelope,
    validate_operation,
)
from torbox.formatters import print_dict_panel, print_panel, print_table

app = typer.Typer(help="Web download management commands")


@app.command(
    help="GET /webdl/mylist — List all web downloads. Example: torbox webdl list"
)
@handle_errors
def list(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset"),
    limit: int = typer.Option(1000, "--limit", help="Pagination limit"),
) -> None:
    client = _get_client(ctx)
    params: dict[str, str | int] = {"offset": offset, "limit": limit}
    data: dict[str, Any] = client.get("/webdl/mylist", params=params)
    print_json_envelope(ctx, data, "webdl list", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if isinstance(data.get("data"), builtins.list):
        if not _is_quiet(ctx):
            print_table(data["data"], "Web Downloads")
    elif not _is_quiet(ctx):
        print("WebDL list: OK")


@app.command(
    help=(
        "POST /webdl/asynccreatewebdownload — Create web download asynchronously. "
        "Returns instantly; errors delivered via notifications. "
        "Example: torbox webdl async-create 'https://example.com/file.zip'"
    )
)
@handle_errors
def async_create(
    ctx: Context,
    link: str,
    password: str | None = typer.Option(
        None, "--password", help="Password if required"
    ),
    name: str | None = typer.Option(
        None, "--name", help="Custom name for the download"
    ),
    as_queued: bool = typer.Option(False, "--as-queued", help="Add as queued download"),
    add_only_if_cached: bool = typer.Option(
        False, "--add-only-if-cached", help="Only add if cached"
    ),
    allow_zip: bool = typer.Option(
        False, "--allow-zip", help="Allow zip format for downloads"
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be sent without making the request"
    ),
) -> None:
    client = _get_client(ctx)
    payload: dict[str, str | int] = {"link": link}
    if password:
        payload["password"] = password
    if name:
        payload["name"] = name
    if as_queued:
        payload["as_queued"] = 1
    if add_only_if_cached:
        payload["add_only_if_cached"] = 1
    if allow_zip:
        payload["allow_zip"] = 1
    if dry_run_guard(
        ctx,
        "POST /webdl/asynccreatewebdownload",
        payload=payload,
        dry_run=dry_run,
    ):
        return
    data: dict[str, Any] = client.post("/webdl/asynccreatewebdownload", data=payload)
    print_json_envelope(ctx, data, "webdl async-create", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    elif not _is_quiet(ctx):
        print_panel(
            "Async web download creation submitted. "
            "Errors delivered via notifications.",
            "Async Created",
        )


@app.command(
    help=(
        "POST /webdl/createwebdownload — Create web download from link. "
        "Example: torbox webdl create 'https://example.com/file.zip'"
    )
)
@handle_errors
def create(
    ctx: Context,
    link: str,
    password: str | None = typer.Option(
        None, "--password", help="Password if required"
    ),
    name: str | None = typer.Option(
        None, "--name", help="Custom name for the download"
    ),
    as_queued: bool = typer.Option(False, "--as-queued", help="Add as queued download"),
    add_only_if_cached: bool = typer.Option(
        False, "--add-only-if-cached", help="Only add if cached"
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be sent without making the request"
    ),
) -> None:
    client = _get_client(ctx)
    payload: dict[str, str | int] = {"link": link}
    if password:
        payload["password"] = password
    if name:
        payload["name"] = name
    if as_queued:
        payload["as_queued"] = 1
    if add_only_if_cached:
        payload["add_only_if_cached"] = 1
    if dry_run_guard(
        ctx, "POST /webdl/createwebdownload", payload=payload, dry_run=dry_run
    ):
        return
    data: dict[str, Any] = client.post("/webdl/createwebdownload", data=payload)
    print_json_envelope(ctx, data, "webdl create", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    elif not _is_quiet(ctx):
        print_panel("Web download created successfully.", "Created")


@app.command(
    help=(
        "POST /webdl/controlwebdownload — Control web download (delete|pause|resume). "
        "Example: torbox webdl control 20 delete --yes"
    )
)
@handle_errors
def control(
    ctx: Context,
    id: int | None = typer.Argument(
        None, help="Web download ID (mutually exclusive with --all)"
    ),
    operation: str = typer.Option(None, "--operation", help="delete | pause | resume"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    all: bool = typer.Option(False, "--all", help="Apply to all web downloads"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be sent without making the request"
    ),
) -> None:
    if not operation:
        raise typer.BadParameter("--operation is required")
    operation = validate_operation(operation)
    if not all and id is None:
        raise typer.BadParameter("Either provide an ID or use --all")
    if all and id is not None:
        raise typer.BadParameter("--all and ID are mutually exclusive")
    payload: dict[str, Any] = {"operation": operation}
    if all:
        payload["all"] = 1
    else:
        payload["webdl_id"] = id
    if dry_run_guard(
        ctx, "POST /webdl/controlwebdownload", payload=payload, dry_run=dry_run
    ):
        return
    if all:
        if not confirm_bulk_destructive(operation, "web download", yes):
            raise typer.Exit(code=0)
    else:
        assert id is not None
        if not confirm_destructive(operation, "web download", id, yes):
            raise typer.Exit(code=0)
    client = _get_client(ctx)
    data: dict[str, Any] = client.post("/webdl/controlwebdownload", json=payload)
    print_json_envelope(ctx, data, "webdl control", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    elif not _is_quiet(ctx):
        print_panel(f"Operation '{operation}' completed successfully.", f"WebDL {id}")


@app.command(
    help="PUT /webdl/editwebdownload — Edit web download. Example: torbox webdl edit 20"
)
@handle_errors
def edit(
    ctx: Context,
    id: int,
    name: str | None = typer.Option(None, "--name", help="New name for the download"),
    tags: str | None = typer.Option(None, "--tags", help="Comma-separated tags"),
    alternative_hashes: str | None = typer.Option(
        None, "--alternative-hashes", help="Comma-separated alternative hashes"
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be sent without making the request"
    ),
) -> None:
    payload: dict[str, str | int] = {"webdl_id": id}
    if name:
        payload["name"] = name
    if tags:
        payload["tags"] = tags
    if alternative_hashes:
        payload["alternative_hashes"] = alternative_hashes
    if dry_run_guard(
        ctx, "PUT /webdl/editwebdownload", payload=payload, dry_run=dry_run
    ):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.put("/webdl/editwebdownload", json=payload)
    print_json_envelope(ctx, data, "webdl edit", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    elif not _is_quiet(ctx):
        print_panel("Web download edited successfully.", f"WebDL {id}")


@app.command(
    help=(
        "GET /webdl/hosters — List supported hosters. "
        "Auth is optional. Example: torbox webdl hosters"
    )
)
@handle_errors
def hosters(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
) -> None:
    client = _get_client(ctx)
    # Auth is optional for hosters; optional_get sends Bearer if available
    data: dict[str, Any] = client.optional_get("/webdl/hosters")
    print_json_envelope(ctx, data, "webdl hosters", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if isinstance(data.get("data"), builtins.list):
        if not _is_quiet(ctx):
            print_table(data["data"], "Hosters")
    elif not _is_quiet(ctx):
        print_panel("Hosters list retrieved.", "Hosters")


@app.command(
    help=(
        "GET /webdl/requestdl — Request download link for webdl file. "
        "Example: torbox webdl requestdl 20 1"
    ),
)
@handle_errors
def requestdl(
    ctx: Context,
    id: int,
    file_id: int = typer.Argument(..., help="File ID within the web download"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    zip_link: bool = typer.Option(False, "--zip-link", help="Request a zip link"),
    user_ip: str | None = typer.Option(None, "--user-ip", help="User IP address"),
    redirect: bool = typer.Option(False, "--redirect", help="Return redirect link"),
    append_name: bool = typer.Option(
        False, "--append-name", help="Append filename to link"
    ),
) -> None:
    client = _get_client(ctx)
    params: dict[str, str | int] = {
        "webdl_id": id,
        "file_id": file_id,
        "token": client.api_key,
    }
    if zip_link:
        params["zip_link"] = 1
    if user_ip:
        params["user_ip"] = user_ip
    if redirect:
        params["redirect"] = 1
    if append_name:
        params["append_name"] = 1
    data: dict[str, Any] = client.get("/webdl/requestdl", params=params)
    print_json_envelope(ctx, data, "webdl requestdl", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    elif not _is_quiet(ctx):
        print_panel("Download link requested.", f"Request DL {id}/{file_id}")


@app.command(
    help=(
        "GET /webdl/checkcached — Check if hash(es) are cached by MD5 of the link. "
        "Example: torbox webdl checkcached a1b2c3d4,e5f6 --format object"
    ),
)
@handle_errors
def checkcached(
    ctx: Context,
    hashes: builtins.list[str],
    format: str | None = typer.Option(
        None, "--format", help="Output format: object | list"
    ),
    list_files: bool = typer.Option(
        False, "--list-files", help="Include list of files in response"
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
) -> None:
    client = _get_client(ctx)
    params: dict[str, str | int] = {"hash": ",".join(hashes)}
    if format:
        params["format"] = format
    if list_files:
        params["list_files"] = 1
    data: dict[str, Any] = client.get("/webdl/checkcached", params=params)
    print_json_envelope(ctx, data, "webdl checkcached", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        item = data.get("data") if isinstance(data, dict) else data
        if isinstance(item, dict):
            print_dict_panel(item, "Cache Status")
        else:
            print_panel("Cache check completed.", "Check Cached")
