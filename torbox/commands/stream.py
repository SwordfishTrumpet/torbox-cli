"""Stream commands: create, data."""

from __future__ import annotations

from typing import Any

import typer
from typer import Context

from torbox.commands._helpers import (
    _get_client,
    _get_field,
    _is_quiet,
    _should_json,
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
) -> None:
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
    if _should_json(ctx, json) or _get_field(ctx):
        print_json_envelope(ctx, data, "stream create", local_json=json)
        return
    elif not _is_quiet(ctx):
        print_panel("Stream created successfully.", f"Stream {type} {id}")


@app.command(
    help=(
        "GET /stream/getstreamdata — Get stream data by token\n\n"
        "Example: torbox stream data abc123"
    )
)
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
) -> None:
    client = _get_client(ctx)
    params: dict[str, str | int] = {"presigned_token": token, "token": client.api_key}
    if chosen_subtitle_index is not None:
        params["chosen_subtitle_index"] = chosen_subtitle_index
    if chosen_audio_index is not None:
        params["chosen_audio_index"] = chosen_audio_index
    if chosen_resolution_index is not None:
        params["chosen_resolution_index"] = chosen_resolution_index
    data: dict[str, Any] = client.get("/stream/getstreamdata", params=params)
    if _should_json(ctx, json) or _get_field(ctx):
        print_json_envelope(ctx, data, "stream data", local_json=json)
        return
    elif not _is_quiet(ctx):
        print_panel("Stream data retrieved.", "Stream Data")
