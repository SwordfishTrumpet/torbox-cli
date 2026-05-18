"""Search commands: stream, library. [Unofficial — Stremio addon]"""

from __future__ import annotations

import re
from typing import Any

import click
import typer
from rich.panel import Panel
from rich.table import Table
from typer import Context
from typer.core import TyperGroup

from torbox.commands._helpers import (
    _get_field,
    _is_quiet,
    _should_json,
    handle_errors,
    print_json_envelope,
)
from torbox.config import load_config
from torbox.formatters import console
from torbox.stremio import (
    StremioClient,
    filter_streams,
)
from torbox.utils import format_size
from torbox.utils import parse_size as _parse_size_util


class SearchGroup(TyperGroup):
    """Typer group that defaults to the 'streams' subcommand."""

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        try:
            return super().resolve_command(ctx, args)
        except Exception:
            cmd_name = "streams"
            return cmd_name, self.get_command(ctx, cmd_name), args


app = typer.Typer(
    cls=SearchGroup,
    help="Search torrent streams and library [Unofficial — Stremio addon]",
    invoke_without_command=True,
    no_args_is_help=True,
)

IMDB_ID_RE = re.compile(r"^tt\d+")
TYPE_CHOICES = ["movie", "series", "anime"]


def _get_stremio_client(ctx: Context) -> StremioClient:
    """Create a StremioClient from CLI context options."""
    api_key = ctx.obj.get("api_key") if ctx.obj else None
    config_path = ctx.obj.get("config") if ctx.obj else None
    profile = ctx.obj.get("profile") if ctx.obj else None
    verbose = ctx.obj.get("verbose", False) if ctx.obj else False
    auto_retry = ctx.obj.get("auto_retry", False) if ctx.obj else False

    cfg = load_config(
        api_key_override=api_key,
        config_path=config_path,
        profile=profile,
    )
    resolved_key = cfg.get("api_key")

    return StremioClient(api_key=resolved_key, verbose=verbose, auto_retry=auto_retry)


def _is_imdb_id(value: str) -> bool:
    return bool(IMDB_ID_RE.match(value))


def _print_stream_table(
    streams: list[dict[str, Any]],
    title: str = "",
    quiet: bool = False,
) -> None:
    if not streams:
        if not quiet:
            console.print("No streams found.")
        return

    table = Table(title=title or "Available Streams")
    table.add_column("#", style="dim", width=4)
    table.add_column("Filename", max_width=45)
    table.add_column("Quality")
    table.add_column("Size")
    table.add_column("Seeders", justify="right")
    table.add_column("Source")
    table.add_column("Group", max_width=15)
    table.add_column("Year", justify="right")
    table.add_column("Cached")

    for i, s in enumerate(streams, 1):
        p = s.get("_parsed", {})
        filename = p.get("filename", s.get("behaviorHints", {}).get("filename", ""))
        if len(filename) > 45:
            filename = filename[:42] + "..."

        table.add_row(
            str(i),
            filename,
            p.get("quality", ""),
            format_size(s.get("behaviorHints", {}).get("videoSize", 0)),
            str(p.get("seeders", 0)),
            p.get("source", ""),
            p.get("release_group", ""),
            str(p.get("year", "") or ""),
            "\u2713" if p.get("cached") else "",
        )

    console.print(table)


def _print_library_table(
    metas: list[dict[str, Any]],
    title: str = "",
    quiet: bool = False,
) -> None:
    if not metas:
        if not quiet:
            console.print("No library items found.")
        return

    table = Table(title=title or "Library Results")
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", max_width=50)
    table.add_column("Size")
    table.add_column("Type")
    table.add_column("File ID", justify="right")

    for i, m in enumerate(metas, 1):
        name = m.get("name", "")
        if len(name) > 50:
            name = name[:47] + "..."

        table.add_row(
            str(i),
            name,
            format_size(m.get("file_size", 0)),
            m.get("type", ""),
            str(m.get("file_id", "")),
        )

    console.print(table)


def _print_cinemeta_table(
    metas: list[dict[str, Any]],
    query: str,
) -> None:
    table = Table(title=f'Matches for "{query}"')
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", max_width=35)
    table.add_column("Year", justify="right")
    table.add_column("Rating", justify="right")
    table.add_column("Genre", max_width=20)
    table.add_column("Type")
    table.add_column("IMDB ID")

    for i, m in enumerate(metas, 1):
        name = m.get("name", "")
        if len(name) > 35:
            name = name[:32] + "..."

        # Some results have imdbRating inline; meta endpoint always does.
        rating = m.get("imdbRating", "")
        genres = m.get("genres", m.get("genre", []))
        genre_str = ", ".join(genres) if isinstance(genres, list) else str(genres)
        if len(genre_str) > 20:
            genre_str = genre_str[:17] + "..."

        table.add_row(
            str(i),
            name,
            str(m.get("year", "")),
            str(rating),
            genre_str,
            m.get("type", ""),
            m.get("id", ""),
        )

    console.print(table)


def _resolve_to_imdb(
    query: str,
    type: str,
    first: bool = False,
    quiet: bool = False,
    genre: str | None = None,
) -> str | None:
    try:
        result = StremioClient.cinemeta_search(query, type)
    except Exception:
        if not quiet:
            console.print(
                "[red]Could not resolve title via Cinemeta. "
                "Try using an IMDB ID directly: torbox search tt1234567[/red]"
            )
        return None

    metas = result.get("metas", [])
    if not metas:
        if not quiet:
            console.print(f"No matches found for '{query}'.")
        return None

    if genre:
        genre_lower = genre.lower()
        metas = [
            m
            for m in metas
            if genre_lower in ", ".join(m.get("genres", m.get("genre", []))).lower()
            if isinstance(m.get("genres", m.get("genre", [])), list)
            or genre_lower in str(m.get("genre", "")).lower()
        ]
        if not metas:
            if not quiet:
                console.print(
                    f"[yellow]No matches in genre '{genre}' for '{query}'.[/yellow]"
                )
            return None

    if first or len(metas) == 1:
        return str(metas[0].get("id", "")) or None

    _print_cinemeta_table(metas[:10], query)

    while True:
        try:
            choice = typer.prompt(
                f"Enter number (1-{min(len(metas), 10)}) or q to quit"
            )
            if choice.lower() == "q":
                return None
            idx = int(choice) - 1
            if 0 <= idx < min(len(metas), 10):
                return str(metas[idx].get("id", "")) or None
            console.print(f"[red]Invalid choice. Enter 1-{min(len(metas), 10)}.[/red]")
        except (ValueError, typer.Abort):
            return None


def _parse_id_and_se(
    query: str,
    season: int | None = None,
    episode: int | None = None,
) -> tuple[str, int | None, int | None]:
    if ":" in query:
        parts = query.split(":")
        if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
            return parts[0], int(parts[1]), int(parts[2])
    return query, season, episode


@app.callback(invoke_without_command=True)
def search_callback(ctx: Context) -> None:
    """Search torrent streams and library [Unofficial — Stremio addon].

    Use subcommands:
      torbox search streams <query> — Find torrents for a title or IMDB ID
      torbox search library <query> — Search your TorBox library

    Warning: This uses TorBox's Stremio addon endpoints,
    which are unofficial and may change.
    """
    if ctx.invoked_subcommand is not None:
        return
    raise typer.Exit()


@app.command(help="Search torrent streams by title or IMDB ID")
@handle_errors
def streams(
    ctx: Context,
    query: str = typer.Argument(..., help="Title or IMDB ID to search"),
    type: str = typer.Option("movie", "-t", "--type"),  # noqa: A002
    season: int | None = typer.Option(None, "-s", "--season"),
    episode: int | None = typer.Option(None, "-e", "--episode"),
    first: bool = typer.Option(False, "--first"),
    resolution: str | None = typer.Option(None, "--resolution"),
    cached: bool | None = typer.Option(None, "--cached/--not-cached"),
    min_size: str | None = typer.Option(None, "--min-size"),
    max_size: str | None = typer.Option(None, "--max-size"),
    min_seeders: int | None = typer.Option(None, "--min-seeders"),
    quality: str | None = typer.Option(None, "--quality"),
    source: str | None = typer.Option(None, "--source"),
    sort: str | None = typer.Option(None, "--sort"),
    limit: int = typer.Option(20, "--limit"),
    genre: str | None = typer.Option(
        None, "--genre", help="Filter Cinemeta results by genre"
    ),
    details: bool = typer.Option(
        False, "--details", help="Show Cinemeta metadata before streams"
    ),
    json: bool = typer.Option(False, "--json", "-j"),
    field: str | None = typer.Option(None, "--field", "-f"),
) -> None:
    """Search torrent streams for a movie, series, or anime.

    Supports both title strings (auto-resolved via Cinemeta) and
    direct IMDB IDs.

    Warning: This uses TorBox's Stremio addon endpoints,
    which are unofficial and may change.

    Examples:
        torbox search streams "the matrix"
        torbox search streams tt0133093
        torbox search streams tt0133093 --resolution 1080p --cached
        torbox search streams tt0133093 --min-seeders 100 --sort seeders
    """
    if type not in TYPE_CHOICES:
        raise typer.BadParameter(f"Type must be one of: {', '.join(TYPE_CHOICES)}")

    imdb_id, s, e = _parse_id_and_se(query, season, episode)
    quiet = _is_quiet(ctx)

    if not _is_imdb_id(imdb_id):
        if not quiet:
            console.print(f'[dim]Resolving "{query}" via Cinemeta...[/dim]')
        resolved = _resolve_to_imdb(query, type, first=first, quiet=quiet, genre=genre)
        if not resolved:
            raise typer.Exit(code=1)
        imdb_id = resolved
        if not quiet:
            console.print(f"[dim]Using IMDB ID: {imdb_id}[/dim]")

    _run_stream_search(
        ctx,
        imdb_id=imdb_id,
        type=type,
        season=s,
        episode=e,
        resolution=resolution,
        cached=cached,
        min_size=min_size,
        max_size=max_size,
        min_seeders=min_seeders,
        quality=quality,
        source=source,
        sort=sort,
        limit=limit,
        json=json,
        field=field,
        details=details,
        quiet=quiet,
    )


@app.command(help="Search your TorBox library by filename")
@handle_errors
def library(
    ctx: Context,
    query: str = typer.Argument(..., help="Filename or partial name to search"),
    type: str = typer.Option("movie", "-t", "--type"),
    limit: int = typer.Option(20, "--limit", help="Max results to show"),
    json: bool = typer.Option(False, "--json", "-j", help="Emit raw JSON"),
    field: str | None = typer.Option(
        None, "--field", "-f", help="Extract dot-path field"
    ),
) -> None:
    """Search your TorBox library for files matching the query.

    Warning: This uses TorBox's Stremio addon endpoints,
    which are unofficial and may change.
    """
    if type not in TYPE_CHOICES:
        raise typer.BadParameter(f"Type must be one of: {', '.join(TYPE_CHOICES)}")

    client = _get_stremio_client(ctx)
    quiet = _is_quiet(ctx)

    data = client.library_search(query, type=type)
    metas = data.get("metas", [])[:limit]

    print_json_envelope(
        ctx,
        {"metas": metas},
        "search library",
        local_json=json,
        field=field,
    )
    if _should_json(ctx, json) or _get_field(ctx, field):
        return

    if not metas:
        if not quiet:
            console.print(
                "[yellow]Your TorBox library is empty or no results matched.[/yellow]"
            )
        return

    _print_library_table(metas, title=f'Library matches for "{query}"', quiet=quiet)


@app.command(help="Browse popular movies or series via Cinemeta")
@handle_errors
def popular(
    ctx: Context,
    type: str = typer.Option("movie", "-t", "--type"),  # noqa: A002
    limit: int = typer.Option(10, "--limit", help="Max results to show"),
    json: bool = typer.Option(False, "--json", "-j"),
    field: str | None = typer.Option(None, "--field", "-f"),
) -> None:
    """Browse popular movies or series from Cinemeta.

    After showing results, pick a number to search streams for that title.
    """
    if type not in TYPE_CHOICES:
        raise typer.BadParameter(f"Type must be one of: {', '.join(TYPE_CHOICES)}")

    quiet = _is_quiet(ctx)

    try:
        result = StremioClient.cinemeta_popular(type)
    except Exception:
        if not quiet:
            console.print("[red]Could not fetch popular titles from Cinemeta.[/red]")
        raise typer.Exit(code=1)

    metas = result.get("metas", [])[:limit]

    print_json_envelope(
        ctx,
        {"metas": metas},
        "search popular",
        local_json=json,
        field=field,
    )
    if _should_json(ctx, json) or _get_field(ctx, field):
        return

    if not metas:
        if not quiet:
            console.print("[yellow]No popular titles found.[/yellow]")
        return

    _print_cinemeta_table(metas, f"Popular {type}s")

    # Interactive selection → auto stream search
    if not quiet:
        while True:
            try:
                choice = typer.prompt(
                    f"Enter number (1-{len(metas)}) to search streams, or q to quit"
                )
                if choice.lower() == "q":
                    return
                idx = int(choice) - 1
                if 0 <= idx < len(metas):
                    selected = metas[idx]
                    imdb_id = selected.get("id", "")
                    if not imdb_id:
                        console.print("[red]Selected item has no IMDB ID.[/red]")
                        return
                    name = selected.get("name", "")
                    console.print(
                        f"\n[dim]Searching streams for {name} ({imdb_id})...[/dim]\n"
                    )
                    _run_stream_search(
                        ctx,
                        imdb_id=imdb_id,
                        type=type,
                        season=None,
                        episode=None,
                        quiet=quiet,
                    )
                    return
                console.print(f"[red]Invalid choice. Enter 1-{len(metas)}.[/red]")
            except (ValueError, typer.Abort):
                return


@app.command(help="Show full Cinemeta metadata for an IMDB ID")
@handle_errors
def info(
    ctx: Context,
    id: str = typer.Argument(..., help="IMDB ID (e.g. tt0133093)"),  # noqa: A002
    type: str = typer.Option("movie", "-t", "--type"),  # noqa: A002
    json: bool = typer.Option(False, "--json", "-j"),
    field: str | None = typer.Option(None, "--field", "-f"),
) -> None:
    """Fetch and display full Cinemeta metadata for a title.

    Shows description, rating, cast, genres, runtime, and poster URL.
    """
    if type not in TYPE_CHOICES:
        raise typer.BadParameter(f"Type must be one of: {', '.join(TYPE_CHOICES)}")

    quiet = _is_quiet(ctx)

    try:
        result = StremioClient.cinemeta_meta(id, type)
    except Exception:
        if not quiet:
            console.print(
                f"[red]Could not fetch metadata for {id} from Cinemeta.[/red]"
            )
        raise typer.Exit(code=1)

    meta = result.get("meta", {})
    if not meta:
        if not quiet:
            console.print(f"[yellow]No metadata found for {id}.[/yellow]")
        raise typer.Exit(code=1)

    print_json_envelope(
        ctx,
        {"meta": meta},
        "search info",
        local_json=json,
        field=field,
    )
    if _should_json(ctx, json) or _get_field(ctx, field):
        return

    name = meta.get("name", "")
    year = meta.get("year", "")
    rating = meta.get("imdbRating", "")
    runtime = meta.get("runtime", "")
    genres = meta.get("genres", meta.get("genre", []))
    genre_str = ", ".join(genres) if isinstance(genres, list) else str(genres)
    desc = meta.get("description", "")
    cast_list = meta.get("cast", [])
    cast_str = ", ".join(cast_list[:5]) if cast_list else ""
    director_list = meta.get("director", [])
    director_str = ", ".join(director_list) if director_list else ""
    poster = meta.get("poster", "")

    lines = []
    if rating:
        lines.append(f"[bold]Rating:[/bold] {rating}")
    if runtime:
        lines.append(f"[bold]Runtime:[/bold] {runtime}")
    if genre_str:
        lines.append(f"[bold]Genres:[/bold] {genre_str}")
    if director_str:
        lines.append(f"[bold]Director:[/bold] {director_str}")
    if cast_str:
        lines.append(f"[bold]Cast:[/bold] {cast_str}")
    if poster:
        lines.append(f"[bold]Poster:[/bold] {poster}")
    if desc:
        lines.append("")
        lines.append(desc)

    title = f"[bold]{name}[/bold]"
    if year:
        title += f" ({year})"

    console.print(Panel("\n".join(lines), title=title, border_style="blue"))


def _run_stream_search(
    ctx: Context,
    imdb_id: str,
    type: str,
    season: int | None,
    episode: int | None,
    resolution: str | None = None,
    cached: bool | None = None,
    min_size: str | None = None,
    max_size: str | None = None,
    min_seeders: int | None = None,
    quality: str | None = None,
    source: str | None = None,
    sort: str | None = None,
    limit: int = 20,
    json: bool = False,
    field: str | None = None,
    details: bool = False,
    quiet: bool = False,
) -> None:
    """Execute the full stream search flow and output results."""
    client = _get_stremio_client(ctx)

    # Show metadata details if requested
    if (
        details
        and not quiet
        and not _should_json(ctx, json)
        and not _get_field(ctx, field)
    ):
        try:
            meta = StremioClient.cinemeta_meta(imdb_id, type)
            meta_data = meta.get("meta", {})
            if meta_data:
                name = meta_data.get("name", "")
                year = meta_data.get("year", "")
                rating = meta_data.get("imdbRating", "")
                runtime = meta_data.get("runtime", "")
                genres = meta_data.get("genres", meta_data.get("genre", []))
                genre_str = (
                    ", ".join(genres) if isinstance(genres, list) else str(genres)
                )
                desc = meta_data.get("description", "")
                if desc and len(desc) > 200:
                    desc = desc[:197] + "..."

                header = f"[bold]{name}[/bold]"
                if year:
                    header += f" ({year})"
                sub = []
                if rating:
                    sub.append(f"Rating: {rating}")
                if runtime:
                    sub.append(f"Runtime: {runtime}")
                if genre_str:
                    sub.append(f"Genres: {genre_str}")
                body = "\n".join(sub)
                if desc:
                    body += f"\n\n{desc}"
                console.print(Panel(body, title=header, border_style="blue"))
        except Exception:
            pass

    data = client.stream_search(imdb_id, type=type, season=season, episode=episode)
    streams_data = data.get("streams", [])

    min_bytes = parse_size(min_size) if min_size else None
    max_bytes = parse_size(max_size) if max_size else None

    streams_data = filter_streams(
        streams_data,
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

    print_json_envelope(
        ctx,
        {"streams": streams_data},
        "search streams",
        local_json=json,
        field=field,
    )
    if _should_json(ctx, json) or _get_field(ctx, field):
        return

    if not quiet and not streams_data:
        console.print(f"[yellow]No streams found for '{imdb_id}'.[/yellow]")
        return

    _print_stream_table(
        streams_data,
        title=f"Streams for {imdb_id}",
        quiet=quiet,
    )


def parse_size(s: str) -> int | None:
    """Parse size string, raising BadParameter on invalid format."""
    result = _parse_size_util(s)
    if result is None:
        raise typer.BadParameter(f"Invalid size format: {s!r}. Use like 1GB, 500MB.")
    return result
