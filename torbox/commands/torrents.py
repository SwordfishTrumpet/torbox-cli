"""Torrents commands.

list, info, create, control, checkcached, requestdl, export, search,
async-create, edit.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click
import typer
from typer import Context

from torbox.commands._helpers import (
    _get_client,
    _get_field,
    _is_quiet,
    _is_verbose,
    _should_json,
    confirm_bulk_destructive,
    confirm_destructive,
    dry_run_guard,
    handle_errors,
    print_json_envelope,
    validate_operation,
)
from torbox.formatters import print_dict_panel, print_panel, print_table
from torbox.stremio import (
    StremioClient,
    discover_episodes,
    filter_streams,
    stream_search_bulk,
)
from torbox.utils import parse_size as _parse_size_util


class CheckcachedGroup(typer.core.TyperGroup):
    """Typer group that defaults to the 'hashes' subcommand."""

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        try:
            return super().resolve_command(ctx, args)
        except Exception:
            cmd_name = "hashes"
            return cmd_name, self.get_command(ctx, cmd_name), args


app = typer.Typer(
    help=(
        "Torrent management commands. Supports global --json --field. "
        "list/info use formatters or JSON."
    )
)

checkcached_app = typer.Typer(
    cls=CheckcachedGroup,
    help=(
        "Check cache status by infohash (hashes) or by IMDB ID (show). "
        "Default subcommand is 'hashes'."
    ),
)


@app.command(
    name="list",
    help=(
        "GET /torrents/mylist — List user torrents. "
        "Use -j for JSON, -f data.0.name for field. "
        "Example: torbox torrents list --status completed --limit 10"
    ),
)
@handle_errors
def list_torrents(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset"),
    limit: int = typer.Option(1000, "--limit", help="Pagination limit"),
    status: str | None = typer.Option(None, "--status", help="Filter by status"),
) -> None:
    """List torrents with optional pagination and status filter."""
    client = _get_client(ctx)
    params: dict[str, str | int] = {"offset": offset, "limit": limit}
    if status:
        params["status"] = status
    data: dict[str, Any] = client.get("/torrents/mylist", params=params)
    print_json_envelope(ctx, data, "torrents list", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if isinstance(data.get("data"), list):
        if not _is_quiet(ctx):
            print_table(data["data"], "Torrents")
    elif not _is_quiet(ctx):
        print(data)


@app.command(
    help=(
        "GET /torrents/mylist?id={id} — Torrent info by ID. "
        "Example: torbox torrents info 42"
    )
)
@handle_errors
def info(
    ctx: Context,
    id: int,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
) -> None:
    client = _get_client(ctx)
    data: dict[str, Any] = client.get(f"/torrents/mylist?id={id}")
    print_json_envelope(ctx, data, "torrents info", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    item = data.get("data") if isinstance(data, dict) else data
    if isinstance(item, dict):
        print_dict_panel(item, f"Torrent {id}")
    else:
        print_panel(str(data), f"Torrent {id}")


@app.command(
    help=(
        "POST /torrents/createtorrent — Create from magnet or file. "
        "Example: torbox torrents create --magnet 'magnet:?xt=...'"
    )
)
@handle_errors
def create(
    ctx: Context,
    magnet: str | None = None,
    file: str | None = None,
    name: str | None = typer.Option(None, "--name", help="Custom name for the torrent"),
    seed: int | None = typer.Option(
        None, "--seed", help="Seed option: 1=auto, 2=always, 3=never"
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be sent without making the request"
    ),
) -> None:
    client = _get_client(ctx)
    payload: dict[str, str | int] = {}
    if magnet:
        payload["magnet"] = magnet
    if name:
        payload["name"] = name
    if seed is not None:
        payload["seed"] = seed
    if file:
        path = Path(file)
        if not path.exists():
            raise typer.BadParameter(f"File not found: {file}")
        if dry_run_guard(
            ctx,
            "POST /torrents/createtorrent",
            payload={**payload, "file": file},
            dry_run=dry_run,
        ):
            return
        with path.open("rb") as fh:
            files = {"file": (path.name, fh, "application/x-bittorrent")}
            data: dict[str, Any] = client.post(
                "/torrents/createtorrent", data=payload, files=files
            )
    else:
        if not magnet:
            raise typer.BadParameter("Either --magnet or --file is required")
        if dry_run_guard(
            ctx, "POST /torrents/createtorrent", payload=payload, dry_run=dry_run
        ):
            return
        data = client.post("/torrents/createtorrent", data=payload)
    print_json_envelope(ctx, data, "torrents create", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("Torrent created successfully.", "Created")


@app.command(
    help=(
        "POST /torrents/controltorrent — Control torrent (delete|pause|resume). "
        "Example: torbox torrents control 42 delete --yes"
    )
)
@handle_errors
def control(
    ctx: Context,
    id: int | None = typer.Argument(
        None, help="Torrent ID (mutually exclusive with --all)"
    ),
    operation: str = typer.Option(None, "--operation", help="delete | pause | resume"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    all: bool = typer.Option(False, "--all", help="Apply to all torrents"),
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
        payload["torrent_id"] = id
    if dry_run_guard(
        ctx,
        "POST /torrents/controltorrent",
        payload=payload,
        dry_run=dry_run,
    ):
        return
    if all:
        if not confirm_bulk_destructive(operation, "torrent", yes):
            raise typer.Exit(code=0)
    else:
        assert id is not None
        if not confirm_destructive(operation, "torrent", id, yes):
            raise typer.Exit(code=0)
    client = _get_client(ctx)
    data: dict[str, Any] = client.post("/torrents/controltorrent", json=payload)
    print_json_envelope(ctx, data, "torrents control", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel(f"Operation '{operation}' completed successfully.", f"Torrent {id}")


@checkcached_app.command(
    name="hashes",
    help=(
        "GET|POST /torrents/checkcached — Check if hash(es) cached. "
        "Use --batch for many hashes (POST). "
        "Example: torbox torrents checkcached hashes a1b2c3d4"
    ),
)
@handle_errors
def checkcached_hashes(
    ctx: Context,
    hashes: list[str],
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    batch: bool = typer.Option(
        False, "--batch", help="Use POST for unlimited hash checking"
    ),
) -> None:
    client = _get_client(ctx)
    if batch:
        data: dict[str, Any] = client.post(
            "/torrents/checkcached", json={"hashes": hashes}
        )
    else:
        data = client.get("/torrents/checkcached", params={"hash": ",".join(hashes)})
    print_json_envelope(ctx, data, "torrents checkcached", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        item = data.get("data") if isinstance(data, dict) else data
        if isinstance(item, dict):
            print_dict_panel(item, "Cache Status")
        else:
            print_panel("Cache check completed.", "Check Cached")


def _parse_episodes_filter(episodes: str | None) -> list[int] | None:
    if not episodes:
        return None
    try:
        return [int(e.strip()) for e in episodes.split(",") if e.strip()]
    except ValueError:
        raise typer.BadParameter(
            f"Invalid episodes format: {episodes!r}. Use like 1,2,3"
        )


def _aggregate_episode(streams: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate stream metadata into per-episode summary."""
    if not streams:
        return {
            "cached": False,
            "streams_count": 0,
            "cached_streams_count": 0,
            "best_resolution": None,
            "best_quality": None,
            "best_source": None,
            "best_seeders": 0,
            "best_size": 0,
        }
    cached_streams = [s for s in streams if s.get("_parsed", {}).get("cached")]
    target = cached_streams if cached_streams else streams
    quality_order = {
        "4k": 5,
        "2160p": 5,
        "1080p": 4,
        "720p": 3,
        "480p": 2,
        "unknown": 0,
    }
    best = max(
        target,
        key=lambda s: quality_order.get(
            s.get("_parsed", {}).get("resolution", "unknown").lower(),
            0,
        ),
    )
    parsed = best.get("_parsed", {})
    return {
        "cached": bool(cached_streams),
        "streams_count": len(streams),
        "cached_streams_count": len(cached_streams),
        "best_resolution": parsed.get("resolution"),
        "best_quality": parsed.get("quality"),
        "best_source": parsed.get("source"),
        "best_seeders": parsed.get("seeders", 0),
        "best_size": best.get("behaviorHints", {}).get("videoSize", 0),
    }


@checkcached_app.command(
    name="show",
    help=(
        "Check cache status for TV show episodes by IMDB ID. "
        "Queries Stremio addon per-episode in parallel. "
        "Example: torbox torrents checkcached show tt0944947 --season 1"
    ),
)
@handle_errors
def checkcached_show(
    ctx: Context,
    imdb_id: str = typer.Argument(..., help="IMDB ID (e.g. tt0944947)"),
    season: int | None = typer.Option(None, "-s", "--season", help="Season number"),
    episodes: str | None = typer.Option(
        None,
        "-e",
        "--episodes",
        help="Comma-separated episode numbers (e.g. 1,2,3)",
    ),
    resolution: str | None = typer.Option(None, "--resolution"),
    cached: bool | None = typer.Option(None, "--cached/--not-cached"),
    min_size: str | None = typer.Option(None, "--min-size"),
    max_size: str | None = typer.Option(None, "--max-size"),
    min_seeders: int | None = typer.Option(None, "--min-seeders"),
    quality: str | None = typer.Option(None, "--quality"),
    source: str | None = typer.Option(None, "--source"),
    sort: str | None = typer.Option(None, "--sort"),
    limit: int = typer.Option(
        20, "--limit", help="Max streams to consider per episode"
    ),
    max_workers: int = typer.Option(
        5, "--max-workers", help="Parallel Stremio request workers"
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    field: str | None = typer.Option(
        None,
        "--field",
        "-f",
        help="Dot-path extract e.g. data.0.episode",
    ),
    auto_retry: bool = typer.Option(
        False,
        "--auto-retry",
        help="Auto-retry on 429 rate limits with backoff",
    ),
) -> None:
    """Check cache status for TV show episodes by IMDB ID.

    Discovers episodes via Cinemeta, then queries the TorBox Stremio
    addon for each episode in parallel. Aggregates per-episode cache
    status, best resolution, quality, source, and seeders.

    Supports all standard stream filters (--cached, --resolution,
    --min-seeders, etc.) applied per-episode. Sorts episodes by
    episode number, seeders, quality, or cached status.

    Warning: This uses TorBox's Stremio addon endpoints,
    which are unofficial and may change.
    """
    if auto_retry and ctx.obj is not None:
        ctx.obj["auto_retry"] = True

    quiet = _is_quiet(ctx)

    # 1. Discover episodes
    if not quiet:
        print(f"[dim]Discovering episodes for {imdb_id} via Cinemeta...[/dim]")
    try:
        all_episodes = discover_episodes(imdb_id, season=season)
    except Exception as exc:
        if not quiet:
            print(f"[red]Failed to discover episodes: {exc}[/red]")
        raise typer.Exit(code=1)

    if not all_episodes:
        if not quiet:
            print(f"[yellow]No episodes found for {imdb_id}.[/yellow]")
        raise typer.Exit(code=1)

    # 2. Filter episodes
    episode_filter = _parse_episodes_filter(episodes)
    if episode_filter is not None:
        all_episodes = [ep for ep in all_episodes if ep["episode"] in episode_filter]
        if not all_episodes:
            if not quiet:
                print("[yellow]No episodes matched the requested filter.[/yellow]")
            raise typer.Exit(code=1)

    # 3. Build StremioClient
    api_key = ctx.obj.get("api_key") if ctx.obj else None
    config_path = ctx.obj.get("config") if ctx.obj else None
    profile = ctx.obj.get("profile") if ctx.obj else None
    verbose = _is_verbose(ctx)

    from torbox.config import load_config

    cfg = load_config(
        api_key_override=api_key,
        config_path=config_path,
        profile=profile,
    )
    resolved_key = cfg.get("api_key")
    timeout = cfg.get("timeout", 30.0)
    retries = cfg.get("retries", 2)

    client = StremioClient(
        api_key=resolved_key,
        verbose=verbose,
        auto_retry=auto_retry,
        timeout=timeout,
        retries=retries,
    )

    # 4. Parallel stream search
    if not quiet:
        print(f"[dim]Querying {len(all_episodes)} episode(s) in parallel...[/dim]")
    ep_list = [(ep["season"], ep["episode"]) for ep in all_episodes]
    bulk_results = stream_search_bulk(
        client,
        imdb_id,
        ep_list,
        max_workers=max_workers,
        verbose=verbose,
    )

    # 5. Parse size filters
    min_bytes = _parse_size_util(min_size) if min_size else None
    max_bytes = _parse_size_util(max_size) if max_size else None

    # 6. Aggregate per-episode
    rows: list[dict[str, Any]] = []
    for ep in all_episodes:
        s, e = ep["season"], ep["episode"]
        streams = bulk_results.get((s, e), [])
        filtered = filter_streams(
            streams,
            season=s,
            episode=e,
            resolution=resolution,
            cached=cached,
            min_size=min_bytes,
            max_size=max_bytes,
            min_seeders=min_seeders,
            quality=quality,
            source=source,
            sort=sort,
            limit=limit,
        )
        agg = _aggregate_episode(filtered)
        rows.append(
            {
                "season": s,
                "episode": e,
                "title": ep.get("title", ""),
                **agg,
            }
        )

    # 7. Episode-level cached filter (applied after aggregation)
    if cached is not None:
        rows = [r for r in rows if r["cached"] == cached]

    # 8. Sort episodes
    if sort == "seeders":
        rows.sort(key=lambda x: x["best_seeders"], reverse=True)
    elif sort == "quality":
        quality_order = {
            "4k": 5,
            "2160p": 5,
            "1080p": 4,
            "720p": 3,
            "480p": 2,
            "unknown": 0,
        }
        rows.sort(
            key=lambda x: quality_order.get(
                (x["best_resolution"] or "unknown").lower(),
                0,
            ),
            reverse=True,
        )
    elif sort == "cached":
        rows.sort(key=lambda x: (not x["cached"], x["episode"]))
    else:
        rows.sort(key=lambda x: (x["season"], x["episode"]))

    # 9. Output
    payload = {
        "imdb_id": imdb_id,
        "season": season,
        "episodes": rows,
    }
    print_json_envelope(
        ctx,
        payload,
        "torrents checkcached show",
        local_json=json,
        field=field,
    )
    if _should_json(ctx, json) or _get_field(ctx, field):
        return

    if not quiet and not rows:
        print(f"[yellow]No cached streams found for {imdb_id}.[/yellow]")
        return

    if not quiet:
        from torbox.formatters import print_episode_cache_table

        title = f"Cache Status for {imdb_id}"
        if season is not None:
            title += f" — Season {season}"
        print_episode_cache_table(rows, title=title)


@app.command(
    help=(
        "GET /torrents/requestdl — Request download link for file. "
        "Example: torbox torrents requestdl 42 1"
    )
)
@handle_errors
def requestdl(
    ctx: Context,
    id: int,
    file_id: int = typer.Argument(..., help="File ID within the torrent"),
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
        "torrent_id": id,
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
    data: dict[str, Any] = client.get("/torrents/requestdl", params=params)
    print_json_envelope(ctx, data, "torrents requestdl", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        item = data.get("data") if isinstance(data, dict) else data
        if isinstance(item, dict) and "link" in item:
            print_dict_panel(item, f"Download Link {id}/{file_id}")
        else:
            print_panel("Download link requested.", f"Request DL {id}/{file_id}")


@app.command(
    help=(
        "POST /torrents/magnettofile — Export .torrent file. "
        "Fetches the torrent hash, then downloads raw .torrent bytes. "
        "Example: torbox torrents export 42 --output file.torrent"
    )
)
@handle_errors
def export(
    ctx: Context,
    id: int,
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path (default: stdout)"
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
) -> None:
    """Export a .torrent file by ID. Fetches hash first, then raw bytes."""
    client = _get_client(ctx)
    # Step 1: get torrent hash from info endpoint.
    info_data: dict[str, Any] = client.get(f"/torrents/mylist?id={id}")
    item = info_data.get("data") if isinstance(info_data, dict) else info_data
    if not isinstance(item, dict):
        raise typer.BadParameter(f"Torrent {id} not found or invalid response")
    hash_val = item.get("hash")
    if not hash_val:
        raise typer.BadParameter(f"Torrent {id} has no hash available for export")
    magnet = f"magnet:?xt=urn:btih:{hash_val}"
    # Step 2: download raw .torrent bytes via magnet-to-file endpoint.
    resp = client.post_bytes("/torrents/magnettofile", json={"magnet": magnet})
    if _should_json(ctx, json) or _get_field(ctx):
        meta = {
            "success": True,
            "data": {
                "id": id,
                "hash": hash_val,
                "size": len(resp.content),
                "filename": output,
            },
        }
        print_json_envelope(ctx, meta, "torrents export", local_json=json)
        return
    if output:
        Path(output).write_bytes(resp.content)
        if not _is_quiet(ctx):
            print_panel(f"Saved {len(resp.content)} bytes to {output}", f"Export {id}")
    else:
        sys.stdout.buffer.write(resp.content)


@app.command(
    help=(
        "POST /torrents/asynccreatetorrent — Create torrent asynchronously. "
        "Returns instantly; errors delivered via notifications. "
        "Example: torbox torrents async-create --magnet 'magnet:?xt=...'"
    )
)
@handle_errors
def async_create(
    ctx: Context,
    magnet: str | None = None,
    file: str | None = None,
    name: str | None = typer.Option(None, "--name", help="Custom name for the torrent"),
    seed: int | None = typer.Option(
        None, "--seed", help="Seed option: 1=auto, 2=always, 3=never"
    ),
    as_queued: bool = typer.Option(False, "--as-queued", help="Add as queued download"),
    add_only_if_cached: bool = typer.Option(
        False, "--add-only-if-cached", help="Only add if already cached"
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
    payload: dict[str, str | int] = {}
    if magnet:
        payload["magnet"] = magnet
    if name:
        payload["name"] = name
    if seed is not None:
        payload["seed"] = seed
    if as_queued:
        payload["as_queued"] = 1
    if add_only_if_cached:
        payload["add_only_if_cached"] = 1
    if allow_zip:
        payload["allow_zip"] = 1
    if file:
        path = Path(file)
        if not path.exists():
            raise typer.BadParameter(f"File not found: {file}")
        if dry_run_guard(
            ctx,
            "POST /torrents/asynccreatetorrent",
            payload={**payload, "file": file},
            dry_run=dry_run,
        ):
            return
        with path.open("rb") as fh:
            files = {"file": (path.name, fh, "application/x-bittorrent")}
            data: dict[str, Any] = client.post(
                "/torrents/asynccreatetorrent", data=payload, files=files
            )
    else:
        if not magnet:
            raise typer.BadParameter("Either --magnet or --file is required")
        if dry_run_guard(
            ctx,
            "POST /torrents/asynccreatetorrent",
            payload=payload,
            dry_run=dry_run,
        ):
            return
        data = client.post("/torrents/asynccreatetorrent", json=payload)
    print_json_envelope(ctx, data, "torrents async-create", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel(
            "Async torrent creation submitted. Errors delivered via notifications.",
            "Async Created",
        )


@app.command(
    help=(
        "PUT /torrents/edittorrent — Edit a cached torrent. "
        "Example: torbox torrents edit 42 --name 'New Name' --tags 'linux,iso'"
    )
)
@handle_errors
def edit(
    ctx: Context,
    id: int,
    name: str | None = typer.Option(None, "--name", help="New name for the torrent"),
    tags: str | None = typer.Option(None, "--tags", help="Comma-separated tags"),
    alternative_hashes: str | None = typer.Option(
        None,
        "--alternative-hashes",
        help="Comma-separated alternative hashes",
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be sent without making the request",
    ),
) -> None:
    payload: dict[str, Any] = {"torrent_id": id}
    if name is not None:
        payload["name"] = name
    if tags is not None:
        payload["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
    if alternative_hashes is not None:
        payload["alternative_hashes"] = [
            h.strip() for h in alternative_hashes.split(",") if h.strip()
        ]
    if dry_run_guard(
        ctx,
        "PUT /torrents/edittorrent",
        payload=payload,
        dry_run=dry_run,
    ):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.put("/torrents/edittorrent", json=payload)
    print_json_envelope(ctx, data, "torrents edit", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel(f"Torrent {id} edited successfully.", "Edited")


app.add_typer(checkcached_app, name="checkcached")
