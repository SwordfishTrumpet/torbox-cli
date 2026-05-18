"""Torrents commands: list, info, create, control, checkcached, requestdl."""

from __future__ import annotations

from typing import Any

import typer
from typer import Context

from torbox.client import TorBoxClient
from torbox.formatters import print_json, print_table

app = typer.Typer(
    help=(
        "Torrent management commands. Supports global --json --field. "
        "list/info use formatters or JSON."
    )
)


@app.command(
    name="list",
    help=(
        "GET /torrents/mylist — List user torrents. "
        "Use -j for JSON, -f data.0.name for field."
    ),
)
def list_torrents(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
) -> None:
    """List torrents. Respects global ctx for json/field."""
    client: TorBoxClient = TorBoxClient(
        api_key=ctx.obj.get("api_key") if ctx.obj else None
    )
    data: dict[str, Any] = client.get("/torrents/mylist")
    use_json = json or (ctx.obj and ctx.obj.get("json"))
    fld = ctx.obj.get("field") if ctx.obj else None
    if use_json or fld:
        print_json(data, fld)
    else:
        if isinstance(data.get("data"), list):
            print_table(data["data"], "Torrents")
        else:
            print(data)


@app.command(help="GET /torrents/mylist?id={id} — Torrent info by ID")
def info(
    id: int,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output (stub)"),
) -> None:
    client = TorBoxClient()
    data = client.get(f"/torrents/mylist?id={id}")
    print(data if json else f"Torrent {id} info: OK")


@app.command(help="POST /torrents/createtorrent — Create from magnet or file")
def create(
    magnet: str | None = None,
    file: str | None = None,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output (stub)"),
) -> None:
    client = TorBoxClient()
    # stub payload
    data = client.post(
        "/torrents/createtorrent", json={"magnet": magnet} if magnet else {}
    )
    print(data if json else "Torrent created: OK")


@app.command(
    help="POST /torrents/controltorrent — Control torrent (delete|pause|resume)"
)
def control(
    id: int,
    operation: str,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output (stub)"),
) -> None:
    client = TorBoxClient()
    data = client.post(
        "/torrents/controltorrent", json={"torrent_id": id, "operation": operation}
    )
    print(data if json else f"Torrent {id} {operation}: OK")


@app.command(help="GET /torrents/checkcached — Check if hash(es) cached")
def checkcached(
    hashes: list[str],
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output (stub)"),
) -> None:
    client = TorBoxClient()
    data = client.get("/torrents/checkcached", params={"hash": ",".join(hashes)})
    print(data if json else "Cached check: OK")


@app.command(help="GET /torrents/requestdl — Request download link for file")
def requestdl(
    id: int,
    file_id: int,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output (stub)"),
) -> None:
    client = TorBoxClient()
    data = client.get(f"/torrents/requestdl?id={id}&file_id={file_id}")
    print(data if json else f"Download link for {id}/{file_id}: OK")
