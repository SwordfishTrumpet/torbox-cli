"""General commands: status, stats, changelogs, speedtest, docs (no auth)."""

from __future__ import annotations

from typing import Any

import typer
from typer import Context

from torbox.commands._helpers import (
    _get_client,
    _get_field,
    _should_json,
    handle_errors,
    print_json_envelope,
)
from torbox.formatters import print_panel

app = typer.Typer(help="General TorBox API endpoints (public, no auth required)")


@app.command(
    help=(
        "GET /stats — API status and service statistics\n\n"
        "Example: torbox general status"
    )
)
@handle_errors
def status(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Emit raw JSON"),
    field: str | None = typer.Option(
        None, "--field", "-f", help="Extract dot-path field"
    ),
) -> None:
    """Check API status (delegates to /stats since root / returns 404)."""
    client = _get_client(ctx)
    data: dict[str, Any] = client.public_get("/stats")
    print_json_envelope(ctx, data, "general status", local_json=json, field=field)
    if _should_json(ctx, json) or _get_field(ctx, field):
        return
    print_panel(str(data), "Status")


@app.command(
    help="GET /stats — Service statistics\n\nExample: torbox general stats --json"
)
@handle_errors
def stats(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Emit raw JSON"),
    field: str | None = typer.Option(
        None, "--field", "-f", help="Extract dot-path field"
    ),
) -> None:
    client = _get_client(ctx)
    data: dict[str, Any] = client.public_get("/stats")
    print_json_envelope(ctx, data, "general stats", local_json=json, field=field)
    if _should_json(ctx, json) or _get_field(ctx, field):
        return
    print_panel(str(data), "Stats")


@app.command(
    help=(
        "GET /changelogs/json — Recent changelogs\n\nExample: torbox general changelogs"
    )
)
@handle_errors
def changelogs(
    ctx: Context,
    format: str = typer.Option("json", "--format", help="Output format: json or rss"),
    json: bool = typer.Option(False, "--json", "-j", help="Emit raw JSON"),
    field: str | None = typer.Option(
        None, "--field", "-f", help="Extract dot-path field"
    ),
) -> None:
    client = _get_client(ctx)
    if format.lower() == "rss":
        resp = client.public_get_bytes("/changelogs/rss")
        raw_text = resp.text
        print_json_envelope(
            ctx, {"raw": raw_text}, "general changelogs", local_json=json, field=field
        )
        if _should_json(ctx, json) or _get_field(ctx, field):
            return
        print(raw_text)
        return
    data: dict[str, Any] = client.public_get("/changelogs/json")
    print_json_envelope(ctx, data, "general changelogs", local_json=json, field=field)
    if _should_json(ctx, json) or _get_field(ctx, field):
        return
    print_panel(str(data), "Changelogs")


@app.command(
    help=(
        "GET /speedtest — Run speed test\n\n"
        "Example: torbox general speedtest --test-length short --region us"
    )
)
@handle_errors
def speedtest(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Emit raw JSON"),
    field: str | None = typer.Option(
        None, "--field", "-f", help="Extract dot-path field"
    ),
    test_length: str | None = typer.Option(
        None, "--test-length", help="Test length: short or long"
    ),
    region: str | None = typer.Option(None, "--region", help="Region code"),
    user_ip: str | None = typer.Option(None, "--user-ip", help="User IP address"),
) -> None:
    client = _get_client(ctx)
    params: dict[str, str] = {}
    if test_length:
        params["test_length"] = test_length
    if region:
        params["region"] = region
    if user_ip:
        params["user_ip"] = user_ip
    data: dict[str, Any] = client.public_get("/speedtest", params=params)
    print_json_envelope(ctx, data, "general speedtest", local_json=json, field=field)
    if _should_json(ctx, json) or _get_field(ctx, field):
        return
    print_panel(str(data), "Speedtest")


@app.command(help="Generate man page\n\nExample: torbox general docs --man")
@handle_errors
def docs(
    ctx: Context,
    man: bool = typer.Option(False, "--man", help="Output troff man page"),
) -> None:
    if man:
        print(".TH TORBOX 1")
        print(".SH NAME")
        print("torbox \\- TorBox CLI")
    else:
        print("Use --man for man page output")
