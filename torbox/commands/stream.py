"""Stream commands: create, data."""

from __future__ import annotations

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
    validate_stream_type,
)
from torbox.formatters import print_panel

app = typer.Typer(help="Streaming management commands")


@app.command(
    help=(
        "GET /stream/createstream — Create stream token for download\n\n"
        "Example: torbox stream create 42 torrent"
    )
)
@handle_errors
def create(
    ctx: Context,
    id: int,
    type: str = typer.Argument(..., help="torrent|usenet|webdownload"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    file_id: int | None = typer.Option(None, "--file-id", help="File ID to stream"),
    chosen_subtitle_index: int | None = typer.Option(
        None, "--chosen-subtitle-index", help="Subtitle track index"
    ),
    chosen_audio_index: int | None = typer.Option(
        None, "--chosen-audio-index", help="Audio track index"
    ),
    chosen_resolution_index: int | None = typer.Option(
        None, "--chosen-resolution-index", help="Resolution index"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    type = validate_stream_type(type)
    client = _get_client(ctx)
    params: dict[str, str | int] = {"id": id, "type": type}
    if file_id is not None:
        params["file_id"] = file_id
    if chosen_subtitle_index is not None:
        params["chosen_subtitle_index"] = chosen_subtitle_index
    if chosen_audio_index is not None:
        params["chosen_audio_index"] = chosen_audio_index
    if chosen_resolution_index is not None:
        params["chosen_resolution_index"] = chosen_resolution_index
    data: dict[str, Any] = client.get("/stream/createstream", params=params)
    print_json_envelope(ctx, data, "stream create", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("Stream created successfully.", f"Stream {type} {id}")


@app.command(
    help=(
        "DELETE /stream/deletestream — Revoke/delete a stream token\n\n"
        "Example: torbox stream delete abc123 --yes"
    )
)
@handle_errors
def delete(
    ctx: Context,
    token: str,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be sent without making the request"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    if not yes:
        answer = (
            input(f"Are you sure you want to delete stream token {token}? [y/N]: ")
            .strip()
            .lower()
        )
        if answer not in {"y", "yes"}:
            raise typer.Exit(code=0)
    client = _get_client(ctx)
    if dry_run_guard(
        ctx,
        "DELETE /stream/deletestream",
        payload={"token": token},
        dry_run=dry_run,
    ):
        return
    data: dict[str, Any] = client.delete("/stream/deletestream", json={"token": token})
    print_json_envelope(ctx, data, "stream delete", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("Stream token revoked successfully.", f"Stream {token}")


@app.command(
    help=(
        "GET /stream/getstreamdata — Get stream data by token\n\n"
        "Example: torbox stream data abc123"
    )
)
@handle_errors
def data(
    ctx: Context,
    token: str,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    chosen_subtitle_index: int | None = typer.Option(
        None, "--chosen-subtitle-index", help="Subtitle track index"
    ),
    chosen_audio_index: int | None = typer.Option(
        None, "--chosen-audio-index", help="Audio track index"
    ),
    chosen_resolution_index: int | None = typer.Option(
        None, "--chosen-resolution-index", help="Resolution index"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    params: dict[str, str | int] = {"presigned_token": token, "token": client.api_key}
    if chosen_subtitle_index is not None:
        params["chosen_subtitle_index"] = chosen_subtitle_index
    if chosen_audio_index is not None:
        params["chosen_audio_index"] = chosen_audio_index
    if chosen_resolution_index is not None:
        params["chosen_resolution_index"] = chosen_resolution_index
    data: dict[str, Any] = client.get("/stream/getstreamdata", params=params)
    print_json_envelope(ctx, data, "stream data", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("Stream data retrieved.", "Stream Data")
