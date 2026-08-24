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
