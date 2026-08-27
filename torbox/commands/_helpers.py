"""Shared helpers for all command modules to eliminate DRY violations."""

from __future__ import annotations

from typing import Any

import typer
from typer import Context

from torbox.client import TorBoxClient
from torbox.exceptions import TorBoxError
from torbox.formatters import (
    format_envelope,
    print_error_json,
    print_human_error,
    print_json,
)

_CLIENT_ATTR = "_torbox_client"


def _get_client(ctx: Context) -> TorBoxClient:
    """Create a TorBoxClient from CLI context options.

    The created client is cached on ``ctx.obj`` so that duration tracking
    can be read by ``print_json_envelope`` without requiring explicit
    plumbing through every command.
    """
    if ctx.obj and ctx.obj.get(_CLIENT_ATTR):
        client: object = ctx.obj[_CLIENT_ATTR]
        assert isinstance(client, TorBoxClient)
        return client
    client = TorBoxClient(
        api_key=ctx.obj.get("api_key") if ctx.obj else None,
        config_path=ctx.obj.get("config") if ctx.obj else None,
        profile=ctx.obj.get("profile") if ctx.obj else None,
        verbose=ctx.obj.get("verbose", False) if ctx.obj else False,
        auto_retry=ctx.obj.get("auto_retry", False) if ctx.obj else False,
    )
    if ctx.obj is not None:
        ctx.obj[_CLIENT_ATTR] = client
    # Ensure the underlying httpx.Client (and its connection pool) is closed
    # when the CLI context tears down, avoiding leaked sockets.
    call_on_close = getattr(ctx, "call_on_close", None)
    if callable(call_on_close):
        call_on_close(client.close)
    return client


def _should_json(ctx: Context, local_json: bool = False) -> bool:
    """Return True if JSON output is requested globally or locally."""
    if ctx.obj and ctx.obj.get("json"):
        return True
    return bool(local_json)


def _get_field(ctx: Context, local_field: str | None = None) -> str | None:
    """Return the field dot-path, preferring local override then global."""
    if local_field is not None:
        return local_field
    if ctx.obj:
        field = ctx.obj.get("field")
        return field if isinstance(field, str) else None
    return None


def _is_quiet(ctx: Context) -> bool:
    """Return True if --quiet is enabled."""
    if ctx.obj:
        return bool(ctx.obj.get("quiet", False))
    return False


def _is_compact(ctx: Context) -> bool:
    """Return True if --compact is enabled."""
    if ctx.obj:
        return bool(ctx.obj.get("compact", False))
    return False


def _is_verbose(ctx: Context) -> bool:
    """Return True if --verbose is enabled."""
    if ctx.obj:
        return bool(ctx.obj.get("verbose", False))
    return False


def _set_auto_retry(ctx: Context, auto_retry: bool) -> None:
    """Set auto-retry flag on context if enabled."""
    if auto_retry and ctx.obj is not None:
        ctx.obj["auto_retry"] = True


_SECRET_KEY_NAMES = {
    "token",
    "refresh_token",
    "password",
    "passphrase",
    "secret",
    "api_key",
    "apikey",
    "authorization",
}
_SECRET_KEY_SUFFIXES = (
    "_token",
    "_password",
    "_secret",
    "_key",
    "_apikey",
)
_REDACTED = "<redacted>"


def _is_secret_key(key: str) -> bool:
    """Return True if a payload key carries credential material."""
    normalized = key.lower().replace("-", "_")
    if normalized in _SECRET_KEY_NAMES:
        return True
    return any(normalized.endswith(suffix) for suffix in _SECRET_KEY_SUFFIXES)


def redact_secrets(value: Any) -> Any:
    """Recursively replace secret values with a redaction marker.

    Walks nested dicts and lists so payloads that embed credentials in
    sub-objects are protected too. Non-secret values are returned as-is.
    """
    if isinstance(value, dict):
        return {
            key: _REDACTED if _is_secret_key(str(key)) else redact_secrets(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def dry_run_guard(
    ctx: Context,
    action: str,
    payload: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> bool:
    """If --dry-run is enabled, print what would be done and return True.

    Callers should skip the actual request when this returns True.
    Secret-bearing payload keys (tokens, passwords, api keys) are
    redacted before printing so credentials never reach stdout.
    """
    if dry_run:
        print(f"[dry-run] {action}")
        if payload:
            print(f"[dry-run] payload: {redact_secrets(payload)}")
        return True
    return False


def validate_operation(operation: str) -> str:
    """Validate and normalize a control operation."""
    allowed = {"delete", "pause", "resume"}
    op = operation.lower()
    if op not in allowed:
        raise typer.BadParameter(
            f"operation must be one of: {', '.join(sorted(allowed))}"
        )
    return op


def validate_stream_type(type: str) -> str:
    """Validate and normalize a stream type."""
    allowed = {"torrent", "usenet", "webdownload"}
    t = type.lower()
    if t not in allowed:
        raise typer.BadParameter(f"type must be one of: {', '.join(sorted(allowed))}")
    return t


def confirm_destructive(operation: str, resource: str, id: int, yes: bool) -> bool:
    """Prompt for confirmation on destructive operations unless --yes is given."""
    if operation != "delete" or yes:
        return True
    prompt = f"Are you sure you want to delete {resource} {id}? [y/N]: "
    answer = input(prompt).strip().lower()
    return answer in {"y", "yes"}


def confirm_bulk_destructive(operation: str, resource: str, yes: bool) -> bool:
    """Prompt for confirmation on bulk destructive operations unless --yes."""
    if operation != "delete" or yes:
        return True
    prompt = (
        f"Are you sure you want to delete ALL {resource}s? "
        "This cannot be undone. [y/N]: "
    )
    try:
        answer = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in {"y", "yes"}


def _print_error_json(exc: Any) -> None:
    """Print a JSON error payload including the exit_code."""
    print_error_json(exc)


def handle_errors(func: Any) -> Any:
    """Decorator that catches TorBoxError and exits with typed codes.

    Works for commands that receive a typer.Context as the first argument.
    """
    import functools

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        ctx: Context | None = None
        if args and isinstance(args[0], Context):
            ctx = args[0]
        try:
            return func(*args, **kwargs)
        except TorBoxError as exc:
            if ctx is not None and (_should_json(ctx, False) or _get_field(ctx)):
                _print_error_json(exc)
            else:
                verbose = (
                    ctx is not None and bool(ctx.obj.get("verbose", False))
                    if ctx and ctx.obj
                    else False
                )
                print_human_error(exc, verbose=verbose)
            raise typer.Exit(code=exc.exit_code)

    return wrapper


def print_json_envelope(
    ctx: Context,
    data: Any,
    command: str,
    duration_ms: float = 0.0,
    local_json: bool = False,
    field: str | None = None,
) -> None:
    """Print API data wrapped in normalized JSON envelope.

    Respects --field and --compact. Raises typer.Exit(code=1) if
    --field path is missing.

    If ``duration_ms`` is 0.0 (the default), the method will attempt to
    read the actual request duration from the cached client on
    ``ctx.obj`` (set by ``_get_client``).
    """
    use_json = _should_json(ctx, local_json)
    fld = field if field is not None else _get_field(ctx)
    compact = _is_compact(ctx)
    verbose = _is_verbose(ctx)
    if not use_json and not fld:
        return
    if not duration_ms and ctx.obj is not None:
        cached_client: TorBoxClient | None = ctx.obj.get(_CLIENT_ATTR)
        if cached_client is not None:
            duration_ms = cached_client.last_request_duration_ms
    envelope = format_envelope(data, command, duration_ms=duration_ms)
    ok = print_json(envelope, field=fld, compact=compact, verbose=verbose)
    if not ok:
        raise typer.Exit(code=1)
