"""User commands: me, settings, searchengines, transactions, etc."""

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
)
from torbox.formatters import (
    print_dict_panel,
    print_panel,
    print_table,
)

app = typer.Typer(help="User account management")


@app.command(
    help=("GET user data — current authenticated user profile\nExample: torbox user me")
)
@handle_errors
def me(
    ctx: Context,
    settings: bool = typer.Option(
        False, "--settings", help="Include settings in response"
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    endpoint = "/user/me"
    if settings:
        endpoint += "?settings=true"
    data: dict[str, Any] = client.get(endpoint)
    print_json_envelope(ctx, data, "user me", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    item = data.get("data") if isinstance(data, dict) else data
    if isinstance(item, dict):
        print_dict_panel(item, "User")
    else:
        print_panel(str(data), "User")


@app.command(
    help=(
        "GET/PUT /user/settings — Get or update user settings\n"
        "Example: torbox user settings --json"
    )
)
@handle_errors
def settings(
    ctx: Context,
    body: str | None = typer.Option(None, "--body", help="JSON payload for PUT update"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    if body:
        import json as _json

        from torbox.exceptions import ValidationError

        try:
            payload = _json.loads(body)
        except _json.JSONDecodeError as exc:
            raise ValidationError(
                f"Invalid JSON in --body: {exc.msg} (pos {exc.pos})"
            ) from exc
        data: dict[str, Any] = client.put("/user/settings/editsettings", json=payload)
    else:
        data = client.get("/user/me?settings=true")
    print_json_envelope(ctx, data, "user settings", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("Settings retrieved.", "Settings")


@app.command(
    help=(
        "GET /user/settings/searchengines — Manage search engines\n"
        "Example: torbox user searchengines"
    )
)
@handle_errors
def searchengines(
    ctx: Context,
    id: int | None = typer.Option(None, "--id", help="Specific search engine ID"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    endpoint = "/user/settings/searchengines"
    if id is not None:
        endpoint += f"?id={id}"
    data: dict[str, Any] = client.get(endpoint)
    print_json_envelope(ctx, data, "user searchengines", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("Search engines retrieved.", "Search Engines")


@app.command(
    help=(
        "GET /user/transactions — List user transactions\n"
        "Example: torbox user transactions --limit 5"
    )
)
@handle_errors
def transactions(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset"),
    limit: int = typer.Option(1000, "--limit", help="Pagination limit"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    params: dict[str, str | int] = {"offset": offset, "limit": limit}
    data: dict[str, Any] = client.get("/user/transactions", params=params)
    print_json_envelope(ctx, data, "user transactions", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if isinstance(data.get("data"), list):
        if not _is_quiet(ctx):
            print_table(data["data"], "Transactions")
    elif not _is_quiet(ctx):
        print("Transactions: OK")


@app.command(
    help=(
        "GET /user/transaction/pdf?id={id} — Download transaction PDF\n"
        "Example: torbox user transaction-pdf 123 --output invoice.pdf"
    )
)
@handle_errors
def transaction_pdf(
    ctx: Context,
    id: int,
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path (default: stdout)"
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    import sys
    from pathlib import Path

    client = _get_client(ctx)
    resp = client.get_bytes("/user/transaction/pdf", params={"transaction_id": id})
    if _should_json(ctx, json) or _get_field(ctx):
        meta: dict[str, Any] = {
            "success": True,
            "data": {
                "transaction_id": id,
                "size": len(resp.content),
                "filename": output,
            },
        }
        print_json_envelope(ctx, meta, "user transaction-pdf", local_json=json)
        return
    if output:
        Path(output).write_bytes(resp.content)
        if not _is_quiet(ctx):
            print_panel(
                f"Saved {len(resp.content)} bytes to {output}",
                f"Transaction PDF {id}",
            )
    else:
        sys.stdout.buffer.write(resp.content)


@app.command(
    help=(
        "GET /user/getconfirmation — Get confirmation code\n"
        "Example: torbox user confirmation"
    )
)
@handle_errors
def confirmation(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    data: dict[str, Any] = client.get("/user/getconfirmation")
    print_json_envelope(ctx, data, "user confirmation", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("Confirmation code retrieved.", "Confirmation")


@app.command(
    help=(
        "GET /user/auth/device/start — Start device auth flow\n"
        "Example: torbox user auth-device-start"
    )
)
@handle_errors
def auth_device_start(
    ctx: Context,
    app: str = typer.Option(
        "Third Party App", "--app", help="App name shown on verification page"
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    params: dict[str, str | int] = {}
    if app:
        params["app"] = app
    # This endpoint does not require authentication per API docs.
    data: dict[str, Any] = client.public_get("/user/auth/device/start", params=params)
    print_json_envelope(ctx, data, "user auth-device-start", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("Device auth flow started.", "Device Auth")


@app.command(
    help=(
        "POST /user/auth/device/token — Get token from device code\n\n"
        "Second step of the device authorization flow: exchange the device\n"
        "code from `auth-device-start` for an API token. No API key required.\n"
        "Example: torbox user auth-device-token dc123"
    )
)
@handle_errors
def auth_device_token(
    ctx: Context,
    device_code: str = typer.Argument(..., help="Device code from auth-device-start"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    payload: dict[str, str] = {"device_code": device_code}
    # This endpoint does not require authentication per API docs.
    data: dict[str, Any] = client.public_post("/user/auth/device/token", json=payload)
    print_json_envelope(ctx, data, "user auth-device-token", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("Device auth token retrieved.", "Device Auth")


@app.command(
    help=(
        "POST /user/refreshtoken — Rotate API token\n\n"
        "Requires session_token from the website's localStorage.\n"
        "Example: torbox user refresh-token session_abc123"
    )
)
@handle_errors
def refresh_token(
    ctx: Context,
    session_token: str = typer.Argument(
        ..., help="Session token from website localStorage"
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request payload without sending"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    payload: dict[str, str] = {"session_token": session_token}
    if dry_run_guard(ctx, "POST /user/refreshtoken", payload=payload, dry_run=dry_run):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.post("/user/refreshtoken", json=payload)
    print_json_envelope(ctx, data, "user refresh-token", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("API token refreshed successfully.", "Token Refreshed")


@app.command(
    help=(
        "POST /user/addreferral — Add a referral code\n\n"
        "Example: torbox user add-referral REFERRAL123"
    )
)
@handle_errors
def add_referral(
    ctx: Context,
    referral_code: str = typer.Argument(..., help="Referral code to add"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request payload without sending"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    payload: dict[str, str] = {"referral_code": referral_code}
    if dry_run_guard(ctx, "POST /user/addreferral", payload=payload, dry_run=dry_run):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.post("/user/addreferral", json=payload)
    print_json_envelope(ctx, data, "user add-referral", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel(
            f"Referral code {referral_code} added successfully.",
            "Referral Added",
        )
