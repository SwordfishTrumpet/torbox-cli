"""Tests for the monitor command — SpeedTracker, MonitorState, helpers."""

from __future__ import annotations

import time
from typing import Any

import pytest
from typer.testing import CliRunner

from torbox.cli import app
from torbox.client import TorBoxClient
from torbox.commands.monitor import (
    MonitorState,
    SpeedTracker,
    _format_eta,
    _format_speed,
    _matches_filter,
    _normalize_items,
    _progress_bar,
    _sort_key,
    _status_style,
)
from torbox.config import DEFAULT_BASE_URL

runner = CliRunner()

TORRENTS = {
    "success": True,
    "data": [
        {
            "id": 1,
            "hash": "a1b2c3",
            "name": "Ubuntu 24.04 ISO",
            "size": 5_000_000_000,
            "status": "completed",
        },
        {
            "id": 2,
            "hash": "d4e5f6",
            "name": "Debian 12 ISO",
            "size": 4_000_000_000,
            "status": "downloading",
        },
    ],
}

USENET = {
    "success": True,
    "data": [
        {"id": 10, "name": "Linux ISO", "status": "downloading", "size": 2_000_000_000}
    ],
}

WEBDL = {
    "success": True,
    "data": [
        {"id": 20, "name": "file.zip", "status": "downloading", "size": 500_000_000}
    ],
}

QUEUED = {
    "success": True,
    "data": [{"id": 5, "type": "torrent", "name": "Music Album", "status": "waiting"}],
}

EMPTY = {"success": True, "data": []}


def _mock_all(httpx_mock: Any, **overrides: Any) -> None:
    b = DEFAULT_BASE_URL
    httpx_mock.add_response(
        url=f"{b}/torrents/mylist?limit=20", json=overrides.get("torrents", TORRENTS)
    )
    httpx_mock.add_response(
        url=f"{b}/usenet/mylist?limit=20", json=overrides.get("usenet", USENET)
    )
    httpx_mock.add_response(
        url=f"{b}/webdl/mylist?limit=20", json=overrides.get("webdl", WEBDL)
    )
    httpx_mock.add_response(
        url=f"{b}/queued/getqueued?limit=20", json=overrides.get("queued", QUEUED)
    )


def _make_client() -> TorBoxClient:
    return TorBoxClient(api_key="dummy")


# =============================================================================
# Helpers
# =============================================================================


class TestNormalizeItems:
    def test_basic(self) -> None:
        items = _normalize_items(TORRENTS, "torrent")
        assert len(items) == 2
        assert items[0]["type"] == "torrent"
        assert items[0]["id"] == 1
        assert items[0]["status"] == "completed"

    def test_progress_from_downloaded(self) -> None:
        items = _normalize_items(
            {"success": True, "data": [{"id": 1, "size": 1000, "downloaded": 250}]}, "t"
        )
        assert items[0]["progress"] == 25.0

    def test_empty(self) -> None:
        assert _normalize_items({}, "x") == []
        assert _normalize_items({"data": []}, "x") == []
        assert _normalize_items({"data": "bad"}, "x") == []

    def test_keeps_api_progress(self) -> None:
        items = _normalize_items(
            {"success": True, "data": [{"id": 1, "size": 1000, "progress": 33.33}]}, "t"
        )
        assert items[0]["progress"] == 33.33

    def test_skips_non_dict(self) -> None:
        items = _normalize_items({"success": True, "data": [{"id": 1}, "bad"]}, "t")
        assert len(items) == 1


class TestStatusStyle:
    def test_all(self) -> None:
        cases = [
            ("downloading", ("DL", "bold green")),
            ("seeding", ("SD", "bold blue")),
            ("paused", ("PA", "bold yellow")),
            ("error", ("ER", "bold red")),
            ("completed", ("OK", "bold green")),
            ("queued", ("WA", "bold cyan")),
            ("waiting", ("WA", "bold cyan")),
            ("uploading", ("UL", "bold magenta")),
            ("stalled", ("ST", "dim")),
            ("metadl", ("MD", "cyan")),
            ("finished", ("FN", "dim")),
            ("unknown", ("UN", "dim")),
            (None, ("UN", "dim")),
            ("whatever", ("WH", "dim")),
        ]
        for status, expected in cases:
            assert _status_style(status) == expected, f"failed for {status!r}"


class TestProgressBar:
    def test_zero(self) -> None:
        assert _progress_bar(0) == "\u2591" * 8

    def test_hundred(self) -> None:
        assert _progress_bar(100) == "\u2588" * 8

    def test_half(self) -> None:
        assert _progress_bar(50) == "\u2588" * 4 + "\u2591" * 4

    def test_custom_width(self) -> None:
        assert len(_progress_bar(33, 10)) == 10


class TestFormatEta:
    @pytest.mark.parametrize(
        "seconds,expected",
        [
            (0, "-"),
            (-1, "-"),
            (5, "5s"),
            (59, "59s"),
            (65, "1m5s"),
            (3661, "1h1m"),
            (86400, "1d"),
        ],
    )
    def test_various(self, seconds: float, expected: str) -> None:
        assert _format_eta(seconds) == expected


class TestFormatSpeed:
    @pytest.mark.parametrize(
        "bps,expected",
        [
            (0, "-"),
            (-1, "-"),
            (500, "500.0 B/s"),
            (1024, "1.0 KB/s"),
            (1_048_576, "1.0 MB/s"),
        ],
    )
    def test_various(self, bps: float, expected: str) -> None:
        assert _format_speed(bps) == expected


class TestMatchesFilter:
    def test_no_filter(self) -> None:
        assert _matches_filter({"name": "x", "status": "y"}, None) is True

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("ubuntu", True),
            ("Ubuntu", True),
            ("Ubuntu 24", True),
            ("windows", False),
            ("completed", True),
        ],
    )
    def test_matches(self, text: str | None, expected: bool) -> None:
        item = {"name": "Ubuntu 24.04 ISO", "status": "completed"}
        assert _matches_filter(item, text) is expected


class TestSortKey:
    def test_status_downloading_first(self) -> None:
        dling = {"status": "downloading", "id": 1}
        seeding = {"status": "seeding", "id": 2}
        assert _sort_key(dling, "status") < _sort_key(seeding, "status")

    @pytest.mark.parametrize("field", ["name", "size", "speed", "progress"])
    def test_does_not_raise(self, field: str) -> None:
        item = {"name": "a", "size": 100, "_speed": 10, "progress": 50}
        _sort_key(item, field)


# =============================================================================
# SpeedTracker
# =============================================================================


class TestSpeedTracker:
    def test_first_call_zero(self) -> None:
        tr = SpeedTracker()
        s, e = tr.update("t", 1, 1000, 50.0, None)
        assert s == 0.0 and e == 0.0

    def test_computes_speed(self) -> None:
        tr = SpeedTracker()
        tr.update("t", 1, 1000, 50.0, None)
        time.sleep(0.05)
        s, e = tr.update("t", 1, 1000, 60.0, None)
        assert s > 0
        assert e > 0

    def test_prefers_api_speed(self) -> None:
        tr = SpeedTracker()
        s, e = tr.update("t", 1, 1000, 50.0, 99999.0)
        assert s == 99999.0

    def test_zero_size(self) -> None:
        tr = SpeedTracker()
        tr.update("t", 1, 0, None, None)
        s, e = tr.update("t", 1, 0, None, None)
        assert s == 0.0 and e == 0.0


# =============================================================================
# MonitorState
# =============================================================================


class TestMonitorState:
    def test_refresh_all_success(self, httpx_mock: Any) -> None:
        _mock_all(httpx_mock)
        state = MonitorState(client=_make_client())
        state.refresh()
        assert len(state.torrents) == 2
        assert len(state.usenet) == 1
        assert len(state.webdl) == 1
        assert len(state.queued) == 1
        assert state.active_count >= 1
        assert state.total_count == 5
        assert not any(
            [
                state.torrents_stale,
                state.usenet_stale,
                state.webdl_stale,
                state.queued_stale,
            ]
        )

    def test_refresh_all_empty(self, httpx_mock: Any) -> None:
        _mock_all(httpx_mock, torrents=EMPTY, usenet=EMPTY, webdl=EMPTY, queued=EMPTY)
        state = MonitorState(client=_make_client())
        state.refresh()
        assert state.torrents == []
        assert state.active_count == 0
        assert state.total_count == 0

    def test_api_failure_sets_stale(self, httpx_mock: Any) -> None:
        b = DEFAULT_BASE_URL
        httpx_mock.add_response(url=f"{b}/torrents/mylist?limit=20", json=TORRENTS)
        httpx_mock.add_response(url=f"{b}/webdl/mylist?limit=20", json=EMPTY)
        httpx_mock.add_response(url=f"{b}/queued/getqueued?limit=20", json=EMPTY)
        httpx_mock.add_response(url=f"{b}/usenet/mylist?limit=20", status_code=500)
        state = MonitorState(client=_make_client())
        state.refresh()
        assert len(state.torrents) == 2
        assert state.usenet_stale is True

    def test_sort_by(self, httpx_mock: Any) -> None:
        _mock_all(httpx_mock)
        state = MonitorState(client=_make_client(), sort_by="speed")
        state.refresh()
        for cat in (state.torrents, state.usenet, state.webdl, state.queued):
            for item in cat:
                assert "_speed" in item
                assert "_eta" in item

    def test_filter_works(self, httpx_mock: Any) -> None:
        _mock_all(httpx_mock)
        state = MonitorState(client=_make_client(), filter_text="ubuntu")
        state.refresh()
        assert all("ubuntu" in t["name"].lower() for t in state.torrents)

    def test_compact(self, httpx_mock: Any) -> None:
        _mock_all(httpx_mock)
        state = MonitorState(client=_make_client(), compact=True)
        state.refresh()
        assert state.compact is True

    def test_render(self, httpx_mock: Any) -> None:
        _mock_all(httpx_mock)
        state = MonitorState(client=_make_client())
        state.refresh()
        r = state.render()
        assert r is not None

    def test_render_empty(self) -> None:
        state = MonitorState(client=_make_client())
        r = state.render()
        assert r is not None


# =============================================================================
# CLI
# =============================================================================


def test_cli_invalid_sort() -> None:
    result = runner.invoke(
        app, ["monitor", "--sort", "invalid"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code != 0
    assert "Invalid sort" in result.output


def test_cli_help() -> None:
    result = runner.invoke(app, ["monitor", "--help"], env={"TORBOX_API_KEY": "dummy"})
    assert result.exit_code == 0
    assert "interval" in result.output
    assert "sort" in result.output
    assert "filter" in result.output
