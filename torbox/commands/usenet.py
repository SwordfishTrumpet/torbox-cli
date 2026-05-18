"""Usenet commands: list, create, control, requestdl."""

from __future__ import annotations

from typing import Any

import typer
from typer import Context

from torbox.commands._helpers import (
    _get_client,
    _get_field,
    _is_quiet,
    _should_json,
    confirm_destructive,
    dry_run_guard,
    handle_errors,
    print_json_envelope,
    validate_operation,
)
from torbox.formatters import print_dict_panel, print_panel, print_table

app = typer.Typer(help="Usenet management commands")


@app.command(
    name="list",
    help=(
        "GET /usenet/mylist — List all usenet downloads. "
        "Example: torbox usenet list --limit 50"
    ),
)
@handle_errors
def list_usenet(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset"),
    limit: int = typer.Option(1000, "--limit", help="Pagination limit"),
) -> None:
    client = _get_client(ctx)
    params: dict[str, str | int] = {"offset": offset, "limit": limit}
    data: dict[str, Any] = client.get("/usenet/mylist", params=params)
    print_json_envelope(ctx, data, "usenet list", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    else:
        if isinstance(data.get("data"), list):
            if not _is_quiet(ctx):
                print_table(data["data"], "Usenet Downloads")
        elif not _is_quiet(ctx):
            print("Usenet list: OK")


@app.command(
    help=(
        "POST /usenet/createusenetdownload — Create usenet download from NZB. "
        "Example: torbox usenet create 'https://example.com/file.nzb'"
    )
)
@handle_errors
def create(
    ctx: Context,
    nzb: str,
    name: str | None = typer.Option(
        None, "--name", help="Custom name for the download"
    ),
    password: str | None = typer.Option(
        None, "--password", help="Password if required"
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be sent without making the request"
    ),
) -> None:
    client = _get_client(ctx)
    # API schema expects "link" (not "nzb") for the NZB URL.
    payload: dict[str, str] = {"link": nzb}
    if name:
        payload["name"] = name
    if password:
        payload["password"] = password
    if dry_run_guard(
        ctx, "POST /usenet/createusenetdownload", payload=payload, dry_run=dry_run
    ):
        return
    data: dict[str, Any] = client.post("/usenet/createusenetdownload", data=payload)
    print_json_envelope(ctx, data, "usenet create", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    elif not _is_quiet(ctx):
        print_panel("Usenet download created successfully.", "Created")


@app.command(
    help=(
        "POST /usenet/controlusenetdownload — Control usenet (delete|pause|resume). "
        "Example: torbox usenet control 10 delete --yes"
    )
)
@handle_errors
def control(
    ctx: Context,
    id: int | None = typer.Argument(
        None, help="Usenet download ID (mutually exclusive with --all)"
    ),
    operation: str = typer.Option(None, "--operation", help="delete | pause | resume"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    all: bool = typer.Option(False, "--all", help="Apply to all usenet downloads"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request payload and exit"
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
        payload["usenet_id"] = id
    if dry_run_guard(
        ctx,
        "POST /usenet/controlusenetdownload",
        payload=payload,
        dry_run=dry_run,
    ):
        return
    if not all:
        assert id is not None
        if not confirm_destructive(operation, "usenet download", id, yes):
            raise typer.Exit(code=0)
    client = _get_client(ctx)
    data: dict[str, Any] = client.post("/usenet/controlusenetdownload", json=payload)
    print_json_envelope(ctx, data, "usenet control", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    elif not _is_quiet(ctx):
        print_panel(f"Operation '{operation}' completed successfully.", f"Usenet {id}")


@app.command(
    help=(
        "GET /usenet/requestdl — Request download link for usenet file. "
        "Example: torbox usenet requestdl 10 1"
    )
)
@handle_errors
def requestdl(
    ctx: Context,
    id: int,
    file_id: int = typer.Argument(..., help="File ID within the usenet download"),
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
        "usenet_id": id,
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
    data: dict[str, Any] = client.get("/usenet/requestdl", params=params)
    print_json_envelope(ctx, data, "usenet requestdl", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    elif not _is_quiet(ctx):
        print_panel("Download link requested.", f"Request DL {id}/{file_id}")


@app.command(
    help=(
        "PUT /usenet/editusenetdownload — Edit cached usenet download metadata. "
        "Example: torbox usenet edit 5 --name 'My Movie' --tags action,hd"
    )
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
    payload: dict[str, str | int] = {"usenet_download_id": id}
    if name:
        payload["name"] = name
    if tags:
        payload["tags"] = tags
    if alternative_hashes:
        payload["alternative_hashes"] = alternative_hashes
    if dry_run_guard(
        ctx, "PUT /usenet/editusenetdownload", payload=payload, dry_run=dry_run
    ):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.put("/usenet/editusenetdownload", json=payload)
    print_json_envelope(ctx, data, "usenet edit", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    elif not _is_quiet(ctx):
        print_panel("Usenet download edited successfully.", f"Usenet {id}")


@app.command(
    help=(
        "POST /usenet/checkcached — Check if usenet hash(es) are cached. "
        "Example: torbox usenet checkcached a1b2c3d4 e5f6g7h8 --list-files"
    )
)
@handle_errors
def checkcached(
    ctx: Context,
    hashes: list[str],
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    format: str | None = typer.Option(
        None, "--format", help="Response format (object | list)"
    ),
    list_files: bool = typer.Option(
        False, "--list-files", help="Include file details in result"
    ),
) -> None:
    client = _get_client(ctx)
    payload: dict[str, Any] = {"hashes": list(hashes)}
    params: dict[str, str | int] = {}
    if format:
        params["format"] = format
    if list_files:
        params["list_files"] = 1
    data: dict[str, Any] = client.post(
        "/usenet/checkcached", json=payload, params=params
    )
    print_json_envelope(ctx, data, "usenet checkcached", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        item = data.get("data") if isinstance(data, dict) else data
        if isinstance(item, dict):
            print_dict_panel(item, "Cache Status")
        else:
            print_panel("Cache check completed.", "Check Cached")
