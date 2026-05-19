"""Rich formatters for human-readable and JSON output."""

from __future__ import annotations

import json as _json
import sys
from datetime import datetime, timezone
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from torbox.utils import format_size

console = Console()


class FieldMissingError(Exception):
    """Raised when a --field dot-path does not resolve."""


def format_envelope(
    data: Any,
    command: str,
    duration_ms: float = 0.0,
    success: bool = True,
    error: str | None = None,
    detail: str | None = None,
    exit_code: int | None = None,
) -> dict[str, Any]:
    """Wrap API response in normalized CLI envelope per TRD section 7.2.

    The envelope shape is:
    {
        "success": true,
        "command": "torrents list",
        "data": <api response>,
        "meta": {
            "timestamp": "2025-08-24T15:18:28Z",
            "request_duration_ms": 245
        }
    }
    """
    return {
        "success": success,
        "command": command,
        "data": data,
        "error": error,
        "detail": detail,
        "exit_code": exit_code,
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_duration_ms": round(duration_ms, 1),
        },
    }


def print_table(
    data: list[dict[str, Any]], title: str = "", columns: list[str] | None = None
) -> None:
    """Print a list of dictionaries as a rich table."""
    if not data:
        console.print("No data")
        return
    table = Table(title=title)
    keys = columns if columns else list(data[0].keys())
    for key in keys:
        table.add_column(str(key))
    for row in data:
        values = [str(row.get(k, "")) for k in keys]
        table.add_row(*values)
    console.print(table)


def print_panel(content: str, title: str = "") -> None:
    """Print a string inside a rich panel."""
    console.print(Panel(content, title=title))


def print_dict_panel(data: dict[str, Any], title: str = "") -> None:
    """Format a dictionary as a key-value panel."""
    lines = [f"{k}: {v}" for k, v in data.items()]
    console.print(Panel("\n".join(lines), title=title))


def print_episode_cache_table(rows: list[dict[str, Any]], title: str = "") -> None:
    """Print a Rich table of per-episode cache status."""
    if not rows:
        console.print("No episodes to display.")
        return
    table = Table(title=title or "Episode Cache Status")
    table.add_column("Season", justify="right")
    table.add_column("Episode", justify="right")
    table.add_column("Title", max_width=40)
    table.add_column("Cached", justify="center")
    table.add_column("Streams", justify="right")
    table.add_column("Cached #", justify="right")
    table.add_column("Resolution")
    table.add_column("Quality")
    table.add_column("Source")
    table.add_column("Seeders", justify="right")
    table.add_column("Size")
    for r in rows:
        table.add_row(
            str(r.get("season", "")),
            str(r.get("episode", "")),
            r.get("title", ""),
            "\u2713" if r.get("cached") else "\u2717",
            str(r.get("streams_count", 0)),
            str(r.get("cached_streams_count", 0)),
            r.get("best_resolution") or "",
            r.get("best_quality") or "",
            r.get("best_source") or "",
            str(r.get("best_seeders", 0)),
            format_size(r.get("best_size", 0)),
        )
    console.print(table)


def print_json(
    data: Any,
    field: str | None = None,
    compact: bool = False,
    verbose: bool = False,
) -> bool:
    """Print data as JSON. If field is specified and missing, print null.

    Returns True if field was found (or no field specified), False otherwise.
    """
    if field:
        try:
            data = extract_field(data, field, verbose=verbose)
        except FieldMissingError as exc:
            print("null")
            if verbose:
                print(
                    f"[verbose] Field extraction failed for {field!r}: {exc}",
                    file=sys.stderr,
                )
            return False
    if compact:
        print(_json.dumps(data, indent=None, separators=(",", ":")))
    else:
        print(_json.dumps(data, indent=2))
    return True


def extract_field(data: Any, field: str, verbose: bool = False) -> Any:
    """Extract a dot-path from nested data.

    Raises FieldMissingError if the path is invalid. When verbose is True,
    the error message includes the traversal path for debugging.
    """
    parts = field.split(".")
    traversed: list[str] = []
    for p in parts:
        traversed.append(p)
        if isinstance(data, list) and p.isdigit():
            idx = int(p)
            if idx < 0 or idx >= len(data):
                msg = f"Index {idx} out of range (list has {len(data)} items)"
                if verbose:
                    msg += f" — traversed: {'.'.join(traversed[:-1]) or 'root'}"
                raise FieldMissingError(msg)
            data = data[idx]
        elif isinstance(data, dict):
            if p not in data:
                available = ", ".join(sorted(data.keys())[:10])
                msg = f"Key {p!r} not found"
                if available:
                    msg += f" — available keys: {available}"
                if verbose:
                    msg += f" — traversed: {'.'.join(traversed[:-1]) or 'root'}"
                raise FieldMissingError(msg)
            data = data[p]
        else:
            msg = f"Cannot traverse {type(data).__name__} at {p!r}"
            if verbose:
                msg += f" — traversed: {'.'.join(traversed[:-1]) or 'root'}"
            raise FieldMissingError(msg)
    return data


def print_error_json(exc: Exception) -> None:
    """Print a JSON error payload including the exit_code."""
    payload = {
        "success": False,
        "error": type(exc).__name__,
        "detail": str(exc),
        "exit_code": getattr(exc, "exit_code", 1),
    }
    print(_json.dumps(payload), file=sys.stderr)


def print_human_error(exc: Exception, verbose: bool = False) -> None:
    """Print a colored, actionable error message to stderr per TRD section 8.

    Example:
        ❌ Authentication failed: BAD_TOKEN
           The provided token is invalid. Check your TORBOX_API_KEY.
    """
    from torbox.exceptions import (
        AuthenticationError,
        DownloadError,
        NotFoundError,
        PlanRestrictedError,
        RateLimitError,
        ServerError,
        ValidationError,
    )

    label = "❌ Error"
    action = ""

    if isinstance(exc, AuthenticationError):
        label = "❌ Authentication failed"
        action = "Check your TORBOX_API_KEY env var, --api-key flag, or config file."
    elif isinstance(exc, ValidationError):
        label = "❌ Validation failed"
        action = "Review the command arguments and try again."
    elif isinstance(exc, NotFoundError):
        label = "❌ Not found"
        action = "Verify the ID exists and you have access to it."
    elif isinstance(exc, RateLimitError):
        label = "❌ Rate limited"
        action = (
            "Wait a moment and retry. Use --auto-retry to enable automatic backoff."
        )
    elif isinstance(exc, PlanRestrictedError):
        label = "❌ Plan restricted"
        action = "Upgrade your TorBox plan or check usage limits."
    elif isinstance(exc, DownloadError):
        label = "❌ Download error"
        action = "Check cooldown/active limits and try again later."
    elif isinstance(exc, ServerError):
        label = "❌ Server error"
        action = "TorBox API encountered an issue. Retry after a short delay."

    msg = str(exc)
    lines = [f"{label}: {msg}"]
    if action:
        lines.append(f"   {action}")
    if verbose:
        import traceback

        tb = traceback.format_exc()
        lines.append("\nVerbose traceback:")
        lines.append(tb)

    print("\n".join(lines), file=sys.stderr)
