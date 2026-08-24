"""NNTP News Server credentials commands: credentials, reset-password."""

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
    handle_errors,
    print_json_envelope,
)
from torbox.formatters import print_panel

app = typer.Typer(help="NNTP News Server credentials management")


@app.command(
    help=(
        "GET /usenet/provider/account — Retrieve News Server login credentials\n\n"
        "Example: torbox nntp credentials"
    )
)
@handle_errors
def credentials(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    data: dict[str, Any] = client.get("/usenet/provider/account")
    print_json_envelope(ctx, data, "nntp credentials", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        item = data.get("data") if isinstance(data, dict) else data
        if isinstance(item, dict):
            from torbox.formatters import print_dict_panel

            print_dict_panel(item, "NNTP Credentials")
        else:
            print_panel("NNTP credentials retrieved.", "Credentials")


@app.command(
    help=(
        "POST /usenet/provider/account/resetpw — Reset News Server password\n\n"
        "Example: torbox nntp reset-password"
    )
)
@handle_errors
def reset_password(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    data: dict[str, Any] = client.post("/usenet/provider/account/resetpw")
    print_json_envelope(ctx, data, "nntp reset-password", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("NNTP password reset successfully.", "Password Reset")
