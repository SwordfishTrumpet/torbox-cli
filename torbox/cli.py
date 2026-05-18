"""Main Typer CLI app for TorBox."""

from __future__ import annotations

import typer
from typer import Context

from torbox.commands import general, queued, rss, stream, torrents, usenet, user, webdl

app = typer.Typer(
    help=(
        "TorBox CLI — wrapper for TorBox API v1. "
        "Full --json/-j and --field/-f support for LLM/automation use. "
        "All list/info use rich formatters in human mode. "
        "Exit codes: 0=ok,1=general,2=auth,3=api/err,5=plan,6=notfound."
    )
)


app.add_typer(
    general.app,
    name="general",
    help="General endpoints (no auth) — status, stats, changelogs, speedtest",
)
app.add_typer(
    user.app,
    name="user",
    help="User account, settings, transactions, search engines, auth flows",
)
app.add_typer(
    torrents.app,
    name="torrents",
    help=(
        "Torrent management: list, info, create, control, "
        "checkcached, requestdl, export"
    ),
)
app.add_typer(
    usenet.app,
    name="usenet",
    help="Usenet management: list, create, control, requestdl",
)
app.add_typer(
    webdl.app, name="webdl", help="Web downloads: list, create, control, edit, hosters"
)
app.add_typer(
    rss.app, name="rss", help="RSS: list feeds, items, create/edit/delete feeds"
)
app.add_typer(queued.app, name="queued", help="Queued downloads management and control")
app.add_typer(
    stream.app, name="stream", help="Create streams and fetch stream data for video"
)


@app.callback()
def main(
    ctx: Context,
    api_key: str | None = typer.Option(
        None, "--api-key", "-k", help="Override API key from config/env"
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="Output raw API JSON (primary for agents/LLMs)"
    ),
    field: str | None = typer.Option(
        None, "--field", "-f", help="Dot-path extract e.g. data.0.name or success"
    ),
) -> None:
    """TorBox CLI entry. Global flags apply to all subcommands.
    --json enables machine mode; human uses formatters.
    """
    ctx.obj = {"json": json_output, "field": field, "api_key": api_key}


if __name__ == "__main__":
    app()
