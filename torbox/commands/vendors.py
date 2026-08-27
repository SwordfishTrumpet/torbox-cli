"""Vendors API commands: account, accounts, register, refresh, etc.

Note: the TorBox changelog (v4.9.1) marks the Vendors API as "still very
incomplete and should not yet be used". The endpoints are wrapped for
completeness; treat results with caution.
"""

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
from torbox.formatters import print_dict_panel, print_panel, print_table

app = typer.Typer(help="Vendors API management — partner/vendor account endpoints")


@app.command(
    help=(
        "GET /vendors/account — Get the current vendor account\n\n"
        "Example: torbox vendors account"
    )
)
@handle_errors
def account(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    data: dict[str, Any] = client.get("/vendors/account")
    print_json_envelope(ctx, data, "vendors account", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        item = data.get("data") if isinstance(data, dict) else data
        if isinstance(item, dict):
            print_dict_panel(item, "Vendor Account")
        else:
            print_panel("Vendor account retrieved.", "Vendor Account")


@app.command(
    help=(
        "GET /vendors/getaccounts — List all vendor accounts\n\n"
        "Example: torbox vendors accounts"
    )
)
@handle_errors
def accounts(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    data: dict[str, Any] = client.get("/vendors/getaccounts")
    print_json_envelope(ctx, data, "vendors accounts", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if isinstance(data.get("data"), list):
        if not _is_quiet(ctx):
            print_table(data["data"], "Vendor Accounts")
    elif not _is_quiet(ctx):
        print_panel("Vendor accounts list retrieved.", "Vendor Accounts")


@app.command(
    help=(
        "GET /vendors/getaccount — Get a vendor account by user auth ID\n\n"
        "Example: torbox vendors account-info user_auth_123"
    )
)
@handle_errors
def account_info(
    ctx: Context,
    user_auth_id: str = typer.Argument(..., help="User auth ID"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    data: dict[str, Any] = client.get(
        "/vendors/getaccount", params={"user_auth_id": user_auth_id}
    )
    print_json_envelope(ctx, data, "vendors account-info", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        item = data.get("data") if isinstance(data, dict) else data
        if isinstance(item, dict):
            print_dict_panel(item, f"Vendor Account {user_auth_id}")
        else:
            print_panel(f"Vendor account {user_auth_id} retrieved.", "Vendor Account")


@app.command(
    help=(
        "PATCH /vendors/refresh — Refresh vendor account data\n\n"
        "Example: torbox vendors refresh"
    )
)
@handle_errors
def refresh(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request without sending"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    if dry_run_guard(ctx, "PATCH /vendors/refresh", dry_run=dry_run):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.patch("/vendors/refresh")
    print_json_envelope(ctx, data, "vendors refresh", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("Vendor account refreshed.", "Vendor Refresh")


@app.command(
    help=(
        "POST /vendors/register — Register a new vendor account\n\n"
        "Example: torbox vendors register --vendor-name 'MyApp' "
        "--vendor-url 'https://example.com'"
    )
)
@handle_errors
def register(
    ctx: Context,
    vendor_name: str = typer.Option(..., "--vendor-name", help="Vendor name"),
    vendor_url: str = typer.Option(..., "--vendor-url", help="Vendor URL"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request without sending"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    payload: dict[str, str] = {"vendor_name": vendor_name, "vendor_url": vendor_url}
    if dry_run_guard(ctx, "POST /vendors/register", payload=payload, dry_run=dry_run):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.post("/vendors/register", json=payload)
    print_json_envelope(ctx, data, "vendors register", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel(f"Vendor {vendor_name} registered.", "Vendor Registered")


@app.command(
    help=(
        "POST /vendors/registeruser — Register a new vendor user\n\n"
        "Example: torbox vendors register-user --user-email user@example.com"
    )
)
@handle_errors
def register_user(
    ctx: Context,
    user_email: str = typer.Option(..., "--user-email", help="User email"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request without sending"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    payload: dict[str, str] = {"user_email": user_email}
    if dry_run_guard(
        ctx, "POST /vendors/registeruser", payload=payload, dry_run=dry_run
    ):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.post("/vendors/registeruser", json=payload)
    print_json_envelope(ctx, data, "vendors register-user", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel(f"Vendor user {user_email} registered.", "Vendor User Registered")


@app.command(
    help=(
        "DELETE /vendors/removeuser — Remove a vendor user\n\n"
        "Example: torbox vendors remove-user user_auth_123 --yes"
    )
)
@handle_errors
def remove_user(
    ctx: Context,
    user_auth_id: str = typer.Argument(..., help="User auth ID to remove"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request without sending"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    if dry_run_guard(
        ctx,
        f"DELETE /vendors/removeuser?user_auth_id={user_auth_id}",
        dry_run=dry_run,
    ):
        return
    if not yes:
        prompt = f"Are you sure you want to remove vendor user {user_auth_id}? [y/N]: "
        answer = input(prompt).strip().lower()
        if answer not in {"y", "yes"}:
            raise typer.Exit(code=0)
    client = _get_client(ctx)
    data: dict[str, Any] = client.delete(
        "/vendors/removeuser", params={"user_auth_id": user_auth_id}
    )
    print_json_envelope(ctx, data, "vendors remove-user", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel(f"Vendor user {user_auth_id} removed.", "Vendor User Removed")


@app.command(
    help=(
        "PUT /vendors/updateaccount — Update vendor account details\n\n"
        "Example: torbox vendors update-account --vendor-name 'MyApp'"
    )
)
@handle_errors
def update_account(
    ctx: Context,
    vendor_name: str | None = typer.Option(None, "--vendor-name", help="Vendor name"),
    vendor_url: str | None = typer.Option(None, "--vendor-url", help="Vendor URL"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request without sending"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    payload: dict[str, str] = {}
    if vendor_name:
        payload["vendor_name"] = vendor_name
    if vendor_url:
        payload["vendor_url"] = vendor_url
    if dry_run_guard(
        ctx, "PUT /vendors/updateaccount", payload=payload, dry_run=dry_run
    ):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.put("/vendors/updateaccount", json=payload)
    print_json_envelope(ctx, data, "vendors update-account", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("Vendor account updated.", "Vendor Account Updated")
