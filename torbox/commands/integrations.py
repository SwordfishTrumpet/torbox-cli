"""Integrations commands: jobs, cancel."""

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

app = typer.Typer(help="Integrations management — cloud upload jobs")


@app.command(
    help=(
        "GET /integration/job/{job_id} — Get a single integration job by ID\n\n"
        "Example: torbox integrations info job_abc123"
    )
)
@handle_errors
def info(
    ctx: Context,
    job_id: str,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
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
        f"GET /integration/job/{job_id}",
        payload={"job_id": job_id},
        dry_run=dry_run,
    ):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.get(f"/integration/job/{job_id}")
    print_json_envelope(ctx, data, "integrations info", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        item = data.get("data") if isinstance(data, dict) else data
        if isinstance(item, dict):
            print_dict_panel(item, f"Integration Job {job_id}")
        else:
            print_panel(f"Integration job {job_id} retrieved.", "Job Info")


@app.command(
    help=(
        "GET /integration/jobs/{hash} — Get integration jobs for a download hash\n\n"
        "Example: torbox integrations jobs abc123def456"
    )
)
@handle_errors
def jobs(
    ctx: Context,
    hash: str,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    data: dict[str, Any] = client.get(f"/integration/jobs/{hash}")
    print_json_envelope(ctx, data, "integrations jobs", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if isinstance(data.get("data"), list):
        if not _is_quiet(ctx):
            print_table(data["data"], "Integration Jobs")
    elif not _is_quiet(ctx):
        print_dict_panel(data.get("data", {}), f"Integration Jobs for {hash}")


@app.command(
    help=(
        "DELETE /integration/job/{job_id} — Cancel an integration job\n\n"
        "Example: torbox integrations cancel job_abc123 --yes"
    )
)
@handle_errors
def cancel(
    ctx: Context,
    job_id: str,
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
        f"DELETE /integration/job/{job_id}",
        payload={"job_id": job_id},
        dry_run=dry_run,
    ):
        return
    if not yes:
        answer = (
            input(f"Are you sure you want to cancel integration job {job_id}? [y/N]: ")
            .strip()
            .lower()
        )
        if answer not in {"y", "yes"}:
            raise typer.Exit(code=0)
    client = _get_client(ctx)
    data: dict[str, Any] = client.delete(f"/integration/job/{job_id}")
    print_json_envelope(ctx, data, "integrations cancel", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("Integration job cancelled.", f"Job {job_id}")


_VALID_PROVIDERS = {
    "googledrive": "/integration/googledrive",
    "pixeldrain": "/integration/pixeldrain",
    "onedrive": "/integration/onedrive",
    "gofile": "/integration/gofile",
    "1fichier": "/integration/1fichier",
    "dropbox": "/integration/dropbox",
}


@app.command(
    help=(
        "POST /integration/{provider} — Queue cloud upload for a file\n\n"
        "Supported providers: googledrive, pixeldrain, onedrive, gofile, "
        "1fichier, dropbox\n\n"
        "Example: torbox integrations upload googledrive 42 --token gtoken\n"
        "         torbox integrations upload dropbox 42 --dropbox-token dbtoken"
    )
)
@handle_errors
def upload(
    ctx: Context,
    provider: str = typer.Argument(
        ...,
        help=(
            "Provider: googledrive, pixeldrain, onedrive, gofile, "
            "1fichier, dropbox"
        ),
    ),
    file_id: int = typer.Argument(..., help="File ID to upload"),
    zip_link: str | None = typer.Option(None, "--zip-link", help="Zip link URL"),
    token: str | None = typer.Option(
        None, "--token", help="OAuth token (googledrive/onedrive)"
    ),
    gofile_token: str | None = typer.Option(
        None, "--gofile-token", help="GoFile token"
    ),
    onefichier_token: str | None = typer.Option(
        None, "--onefichier-token", help="1Fichier token"
    ),
    dropbox_token: str | None = typer.Option(
        None, "--dropbox-token", help="Dropbox OAuth token"
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request without sending"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    provider_lower = provider.lower()
    if provider_lower not in _VALID_PROVIDERS:
        valid = ", ".join(sorted(_VALID_PROVIDERS))
        raise typer.BadParameter(f"provider must be one of: {valid}")

    endpoint = _VALID_PROVIDERS[provider_lower]
    payload: dict[str, Any] = {"file_id": file_id}
    if zip_link:
        payload["zip_link"] = zip_link
    if token:
        key = "google_token" if provider_lower == "googledrive" else "onedrive_token"
        payload[key] = token
    if gofile_token:
        payload["gofile_token"] = gofile_token
    if onefichier_token:
        payload["onefichier_token"] = onefichier_token
    if dropbox_token:
        payload["dropbox_token"] = dropbox_token

    if dry_run_guard(ctx, f"POST {endpoint}", payload=payload, dry_run=dry_run):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.post(endpoint, json=payload)
    print_json_envelope(ctx, data, "integrations upload", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        msg = f"Upload queued to {provider_lower} for file {file_id}."
        print_panel(msg, "Upload Queued")


@app.command(
    help=(
        "GET /integration/jobs — List all integration jobs\n\n"
        "Example: torbox integrations list-jobs"
    )
)
@handle_errors
def list_jobs(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    data: dict[str, Any] = client.get("/integration/jobs")
    print_json_envelope(ctx, data, "integrations list-jobs", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if isinstance(data.get("data"), list):
        if not _is_quiet(ctx):
            print_table(data["data"], "All Integration Jobs")
    elif not _is_quiet(ctx):
        print_panel("Integration jobs list retrieved.", "Integration Jobs")


oauth_app = typer.Typer(
    help="Integration OAuth lifecycle — list, register, unregister, callback, success"
)


@oauth_app.command(
    name="list",
    help=(
        "GET /integration/oauth/me — List your OAuth integrations\n\n"
        "Example: torbox integrations oauth list"
    ),
)
@handle_errors
def oauth_list(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    data: dict[str, Any] = client.get("/integration/oauth/me")
    print_json_envelope(ctx, data, "integrations oauth list", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        item = data.get("data") if isinstance(data, dict) else data
        if isinstance(item, dict):
            print_dict_panel(item, "OAuth Integrations")
        else:
            print_panel("OAuth integrations retrieved.", "OAuth")


@oauth_app.command(
    name="info",
    help=(
        "GET /integration/oauth/{provider} — OAuth status for a provider\n\n"
        "Example: torbox integrations oauth info googledrive"
    ),
)
@handle_errors
def oauth_info(
    ctx: Context,
    provider: str = typer.Argument(..., help="Provider name"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    data: dict[str, Any] = client.get(f"/integration/oauth/{provider}")
    print_json_envelope(ctx, data, "integrations oauth info", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        item = data.get("data") if isinstance(data, dict) else data
        if isinstance(item, dict):
            print_dict_panel(item, f"OAuth {provider}")
        else:
            print_panel(f"OAuth status for {provider} retrieved.", "OAuth")


@oauth_app.command(
    name="register",
    help=(
        "POST /integration/oauth/{provider}/register — Register an OAuth "
        "integration\n\n"
        "Example: torbox integrations oauth register googledrive "
        "--token gtoken --refresh-token grefresh"
    ),
)
@handle_errors
def oauth_register(
    ctx: Context,
    provider: str = typer.Argument(..., help="Provider name"),
    token: str | None = typer.Option(None, "--token", help="OAuth token"),
    refresh_token: str | None = typer.Option(
        None, "--refresh-token", help="OAuth refresh token"
    ),
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
    if token:
        payload["token"] = token
    if refresh_token:
        payload["refresh_token"] = refresh_token
    if dry_run_guard(
        ctx,
        f"POST /integration/oauth/{provider}/register",
        payload=payload,
        dry_run=dry_run,
    ):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.post(
        f"/integration/oauth/{provider}/register", json=payload
    )
    print_json_envelope(ctx, data, "integrations oauth register", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel(f"OAuth integration {provider} registered.", "OAuth")


@oauth_app.command(
    name="callback",
    help=(
        "GET|POST /integration/oauth/{provider}/callback — OAuth callback "
        "endpoint (both methods documented)\n\n"
        "Example: torbox integrations oauth callback googledrive"
    ),
)
@handle_errors
def oauth_callback(
    ctx: Context,
    provider: str = typer.Argument(..., help="Provider name"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request without sending"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    if dry_run_guard(
        ctx, f"GET /integration/oauth/{provider}/callback", dry_run=dry_run
    ):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.get(f"/integration/oauth/{provider}/callback")
    print_json_envelope(ctx, data, "integrations oauth callback", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel(f"OAuth callback for {provider} completed.", "OAuth")


@oauth_app.command(
    name="success",
    help=(
        "GET /integration/oauth/{provider}/success — OAuth success page\n\n"
        "Example: torbox integrations oauth success googledrive"
    ),
)
@handle_errors
def oauth_success(
    ctx: Context,
    provider: str = typer.Argument(..., help="Provider name"),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    client = _get_client(ctx)
    data: dict[str, Any] = client.get(f"/integration/oauth/{provider}/success")
    print_json_envelope(ctx, data, "integrations oauth success", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel(f"OAuth success page for {provider} retrieved.", "OAuth")


@oauth_app.command(
    name="unregister",
    help=(
        "DELETE /integration/oauth/{provider}/unregister — Unregister an OAuth "
        "integration\n\n"
        "Example: torbox integrations oauth unregister googledrive --yes"
    ),
)
@handle_errors
def oauth_unregister(
    ctx: Context,
    provider: str = typer.Argument(..., help="Provider name"),
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
        f"DELETE /integration/oauth/{provider}/unregister",
        dry_run=dry_run,
    ):
        return
    if not yes:
        answer = (
            input(
                f"Are you sure you want to unregister OAuth integration "
                f"{provider}? [y/N]: "
            )
            .strip()
            .lower()
        )
        if answer not in {"y", "yes"}:
            raise typer.Exit(code=0)
    client = _get_client(ctx)
    data: dict[str, Any] = client.delete(f"/integration/oauth/{provider}/unregister")
    print_json_envelope(ctx, data, "integrations oauth unregister", local_json=json)
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel(f"OAuth integration {provider} unregistered.", "OAuth")


@oauth_app.command(
    name="discord-linked-roles",
    help=(
        "POST /integration/oauth/discord/linked_roles — Update Discord "
        "linked roles\n\n"
        "Example: torbox integrations oauth discord-linked-roles "
        "--discord-token dtoken"
    ),
)
@handle_errors
def oauth_discord_linked_roles(
    ctx: Context,
    discord_token: str = typer.Option(
        ..., "--discord-token", help="Discord OAuth token"
    ),
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show request without sending"
    ),
    auto_retry: bool = typer.Option(
        False, "--auto-retry", help="Auto-retry on 429 rate limits with backoff"
    ),
) -> None:
    _set_auto_retry(ctx, auto_retry)
    payload: dict[str, str] = {"discord_token": discord_token}
    if dry_run_guard(
        ctx,
        "POST /integration/oauth/discord/linked_roles",
        payload=payload,
        dry_run=dry_run,
    ):
        return
    client = _get_client(ctx)
    data: dict[str, Any] = client.post(
        "/integration/oauth/discord/linked_roles", json=payload
    )
    print_json_envelope(
        ctx, data, "integrations oauth discord-linked-roles", local_json=json
    )
    if _should_json(ctx, json) or _get_field(ctx):
        return
    if not _is_quiet(ctx):
        print_panel("Discord linked roles updated.", "OAuth")


app.add_typer(oauth_app, name="oauth")
