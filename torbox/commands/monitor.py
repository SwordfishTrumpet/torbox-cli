"""Live monitor command — htop-style TorBox activity dashboard."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import typer
from rich.console import Group, RenderableType
from rich.live import Live
from rich.table import Table
from rich.text import Text
from typer import Context

from torbox.client import TorBoxClient
from torbox.commands._helpers import (
    _get_client,
    _set_auto_retry,
    handle_errors,
)
from torbox.utils import format_size

app = typer.Typer(help="Live monitor — htop-style activity dashboard")

_BADGE_STYLES: dict[str, tuple[str, str]] = {
    "downloading": ("DL", "bold green"),
    "seeding": ("SD", "bold blue"),
    "paused": ("PA", "bold yellow"),
    "error": ("ER", "bold red"),
    "completed": ("OK", "bold green"),
    "queued": ("WA", "bold cyan"),
    "waiting": ("WA", "bold cyan"),
    "uploading": ("UL", "bold magenta"),
    "stalled": ("ST", "dim"),
    "metadl": ("MD", "cyan"),
    "finished": ("FN", "dim"),
}

_TYPE_COLORS: dict[str, str] = {
    "torrent": "cyan",
    "usenet": "green",
    "webdl": "yellow",
    "queued": "magenta",
}

_TYPE_BADGES: dict[str, str] = {
    "torrent": "T",
    "usenet": "U",
    "webdl": "W",
    "queued": "Q",
}

_SORT_KEYS = {"status", "name", "size", "speed", "progress"}


def _status_style(status: str | None) -> tuple[str, str]:
    s = (status or "unknown").lower()
    if s in _BADGE_STYLES:
        return _BADGE_STYLES[s]
    return s[:2].upper(), "dim"


def _progress_bar(pct: float, width: int = 8) -> str:
    if pct <= 0:
        return "\u2591" * width
    if pct >= 100:
        return "\u2588" * width
    filled = int(pct / 100 * width)
    return "\u2588" * filled + "\u2591" * (width - filled)


def _format_eta(seconds: float) -> str:
    if seconds <= 0:
        return "-"
    if seconds >= 86400:
        return f"{int(seconds // 86400)}d"
    if seconds >= 3600:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h{m}m"
    if seconds >= 60:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}m{s}s"
    return f"{int(seconds)}s"


def _format_speed(bytes_per_sec: float) -> str:
    if bytes_per_sec <= 0:
        return "-"
    return format_size(int(bytes_per_sec)) + "/s"


def _matches_filter(item: dict[str, Any], text: str | None) -> bool:
    if not text:
        return True
    t = text.lower()
    name = (item.get("name") or "").lower()
    status = (item.get("status") or "").lower()
    return t in name or t in status


def _sort_key(item: dict[str, Any], sort_by: str) -> tuple[Any, ...]:
    status_order = {
        "downloading": 0,
        "uploading": 1,
        "metaDL": 2,
        "seeding": 3,
        "paused": 4,
        "waiting": 5,
        "queued": 6,
        "completed": 7,
        "finished": 8,
    }
    if sort_by == "name":
        return (0, (item.get("name") or "").lower())
    if sort_by == "size":
        return (0, -(item.get("size") or 0))
    if sort_by == "speed":
        return (0, -(item.get("_speed") or 0))
    if sort_by == "progress":
        return (0, -(item.get("progress") or 0))
    return (
        status_order.get(item.get("status", "").lower(), 99),
        -(item.get("id") or 0),
    )


def _normalize_items(data: Any, item_type: str) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    raw = data.get("data")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        size = item.get("size") or 0
        progress: float | None = item.get("progress")
        if progress is None and size:
            dled = item.get("downloaded")
            if dled is not None and dled >= 0 and size:
                progress = dled / size * 100
        out.append(
            {
                "id": item.get("id"),
                "name": item.get("name", "") or "",
                "type": item_type,
                "status": item.get("status", "unknown") or "unknown",
                "size": size,
                "downloaded": item.get("downloaded"),
                "progress": progress,
                "speed": item.get("download_speed"),
                "eta": item.get("eta"),
            }
        )
    return out


class SpeedTracker:
    """Tracks download progress between ticks to compute speed and ETA."""

    def __init__(self) -> None:
        self._prev: dict[tuple[str, int], tuple[float, float]] = {}

    def update(
        self,
        item_type: str,
        item_id: int,
        size: int | None,
        progress: float | None,
        api_speed: float | None,
    ) -> tuple[float, float]:
        now = time.time()
        key = (item_type, item_id)

        dl = size * (progress / 100.0) if (progress is not None and size) else 0.0

        prev_time, prev_dl = self._prev.get(key, (now, dl))
        self._prev[key] = (now, dl)

        if api_speed and api_speed > 0:
            speed = api_speed
        else:
            delta_t = now - prev_time
            delta_d = dl - prev_dl
            speed = delta_d / delta_t if delta_t > 0 else 0.0
            if speed < 0:
                speed = 0.0

        remaining = (size or 0) - dl
        eta = remaining / speed if speed > 0 and remaining > 0 else 0.0

        return speed, eta


def _build_header(
    active: int, total_speed: float, total_count: int, sort_by: str
) -> Text:
    text = Text()
    text.append(" TorBox Monitor ", style="bold reverse white on blue")
    text.append("  ")
    text.append(f"Active: {active}", style="reverse white on blue")
    text.append("  ")
    text.append(f"DL: {_format_speed(total_speed)}", style="reverse white on blue")
    text.append("  ")
    text.append(f"Items: {total_count}", style="reverse white on blue")
    text.append(" " * 4)
    text.append(f"Sort: {sort_by}", style="reverse dim white on blue")
    text.append("  ")
    text.append("Ctrl-C quit", style="reverse dim white on blue")
    return text


def _build_section(
    title: str,
    items: list[dict[str, Any]],
    stale: bool = False,
    compact: bool = False,
) -> RenderableType:
    parts: list[RenderableType] = []

    header = Text(f" {title}", style="bold underline")
    if items:
        header.append(f" ({len(items)})", style="dim")
    if stale:
        header.append(" [stale]", style="dim red")
    parts.append(header)

    if not items:
        parts.append(Text("  No active items\n", style="dim"))
        return Group(*parts)

    table = Table(box=None, show_edge=False, padding=(0, 1), show_header=True)
    table.add_column("ID", justify="right", width=4, no_wrap=True)
    if not compact:
        table.add_column("", width=2, no_wrap=True)
    table.add_column("Name", max_width=40, no_wrap=True)
    table.add_column("St", width=4, justify="center", no_wrap=True)
    table.add_column("Size", width=8, no_wrap=True)
    table.add_column("Progress", width=12, no_wrap=True)
    if not compact:
        table.add_column("Speed", width=9, no_wrap=True)
        table.add_column("ETA", width=7, no_wrap=True)

    for item in items:
        badge, style = _status_style(item.get("status"))
        pct = item.get("progress") or 0.0
        bar = _progress_bar(pct)
        progress_str = f"{bar} {pct:.0f}%"

        cols: list[RenderableType] = [str(item.get("id", ""))]
        if not compact:
            t = item.get("type", "")
            c = _TYPE_COLORS.get(t, "dim")
            b = _TYPE_BADGES.get(t, "?")
            cols.append(Text(b, style=c))
        cols.append(str(item.get("name", ""))[:40])
        cols.append(Text(badge, style=style))
        cols.append(format_size(item.get("size") or 0) if item.get("size") else "-")
        cols.append(progress_str)
        if not compact:
            cols.append(_format_speed(item.get("_speed", 0.0)))
            cols.append(_format_eta(item.get("_eta", 0.0)))

        table.add_row(*cols)

    parts.append(table)
    return Group(*parts)


class MonitorState:
    """Holds all monitor data and provides refresh/render."""

    def __init__(
        self,
        client: TorBoxClient,
        limit: int = 20,
        sort_by: str = "status",
        filter_text: str | None = None,
        compact: bool = False,
    ) -> None:
        self.client = client
        self.limit = limit
        self.sort_by = sort_by
        self.filter_text = filter_text
        self.compact = compact
        self.tracker = SpeedTracker()

        self.torrents: list[dict[str, Any]] = []
        self.usenet: list[dict[str, Any]] = []
        self.webdl: list[dict[str, Any]] = []
        self.queued: list[dict[str, Any]] = []
        self.torrents_stale = False
        self.usenet_stale = False
        self.webdl_stale = False
        self.queued_stale = False
        self.active_count = 0
        self.total_count = 0

    def refresh(self) -> None:
        endpoints: dict[str, tuple[str, dict[str, str | int]]] = {
            "torrents": ("/torrents/mylist", {"limit": str(self.limit)}),
            "usenet": ("/usenet/mylist", {"limit": str(self.limit)}),
            "webdl": ("/webdl/mylist", {"limit": str(self.limit)}),
            "queued": ("/queued/getqueued", {"limit": str(self.limit)}),
        }

        with ThreadPoolExecutor(max_workers=4) as pool:
            futs: dict[Any, str] = {}
            for key, (ep, params) in endpoints.items():
                futs[pool.submit(self._fetch, ep, params)] = key

            for fut in futs:
                key = futs[fut]
                try:
                    data = fut.result()
                    items = _normalize_items(data, key.rstrip("s"))
                    setattr(self, key, items)
                    setattr(self, f"{key}_stale", False)
                except Exception:
                    setattr(self, f"{key}_stale", True)

        all_items: list[dict[str, Any]] = []
        for cat in ("torrents", "usenet", "webdl", "queued"):
            for item in getattr(self, cat, []):
                speed, eta = self.tracker.update(
                    item.get("type", ""),
                    item.get("id"),
                    item.get("size"),
                    item.get("progress"),
                    item.get("speed"),
                )
                item["_speed"] = item.get("speed") or speed
                item["_eta"] = item.get("eta") or eta
                all_items.append(item)

        if self.filter_text:
            for cat in ("torrents", "usenet", "webdl", "queued"):
                orig = getattr(self, cat)
                filtered = [i for i in orig if _matches_filter(i, self.filter_text)]
                setattr(self, cat, filtered)

        for cat in ("torrents", "usenet", "webdl", "queued"):
            items = getattr(self, cat)
            items.sort(key=lambda i, s=self.sort_by: _sort_key(i, s))

        self.active_count = sum(
            1 for i in all_items if (i.get("status") or "").lower() == "downloading"
        )
        self.total_count = len(all_items)

    def _fetch(self, endpoint: str, params: dict[str, str | int]) -> dict[str, Any]:
        return self.client.get(endpoint, params=params)

    def render(self) -> RenderableType:
        total_speed = sum(
            item.get("_speed", 0.0)
            for cat in (self.torrents, self.usenet, self.webdl, self.queued)
            for item in cat
        )

        elements: list[RenderableType] = [
            _build_header(
                self.active_count, total_speed, self.total_count, self.sort_by
            ),
            Text(""),
        ]

        sections = (
            ("Torrents", self.torrents, self.torrents_stale),
            ("Usenet", self.usenet, self.usenet_stale),
            ("Web Downloads", self.webdl, self.webdl_stale),
            ("Queued", self.queued, self.queued_stale),
        )

        any_data = False
        for title, items, stale in sections:
            if items or stale:
                any_data = True
                elements.append(_build_section(title, items, stale, self.compact))

        if not any_data:
            elements.append(Text("  No downloads found.\n", style="dim"))

        return Group(*elements)


@app.callback(
    invoke_without_command=True,
    help=(
        "Live TUI monitor — htop-style dashboard showing torrents, usenet, "
        "webdl, and queued downloads. Refreshes every N seconds.\n\n"
        "Examples:\n"
        "  torbox monitor\n"
        "  torbox monitor --interval 2 --sort speed\n"
        "  torbox monitor --filter linux --compact"
    ),
)
@handle_errors
def monitor(
    ctx: Context,
    interval: float = typer.Option(
        1.0, "--interval", "-i", help="Refresh interval in seconds"
    ),
    sort: str = typer.Option(
        "status",
        "--sort",
        "-s",
        help="Sort column: status|name|size|speed|progress",
    ),
    filter: str | None = typer.Option(
        None, "--filter", "-f", help="Filter items by name/status substring"
    ),
    limit: int = typer.Option(20, "--limit", "-l", help="Max items per category"),
    compact: bool = typer.Option(
        False, "--compact", help="Fewer columns (hide type badge, speed, ETA)"
    ),
    auto_retry: bool = typer.Option(
        False,
        "--auto-retry",
        help="Auto-retry on 429 rate limits with backoff",
    ),
) -> None:
    """Live TUI monitor — htop-style dashboard."""
    _set_auto_retry(ctx, auto_retry)

    if sort not in _SORT_KEYS:
        valid = ", ".join(sorted(_SORT_KEYS))
        raise typer.BadParameter(f"Invalid sort: {sort!r}. Valid: {valid}")

    client = _get_client(ctx)
    state = MonitorState(
        client=client,
        limit=limit,
        sort_by=sort,
        filter_text=filter,
        compact=compact,
    )

    with Live(screen=True, refresh_per_second=10) as live:
        try:
            while True:
                state.refresh()
                live.update(state.render())
                time.sleep(interval)
        except KeyboardInterrupt:
            pass
