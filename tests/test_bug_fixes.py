"""Tests for the 8 confirmed real-world bugs fixed in this round."""

from __future__ import annotations

from typing import Any

from typer.testing import CliRunner

from torbox.cli import app
from torbox.config import DEFAULT_BASE_URL

runner = CliRunner()


# --- Bug 1 & 2: User endpoints ---


def test_user_me_uses_correct_endpoint(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/me",
        json={"success": True, "data": {"email": "a@b.com"}},
    )
    result = runner.invoke(
        app, ["user", "me", "--json"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code == 0
    assert "a@b.com" in result.output


def test_user_settings_get_uses_correct_endpoint(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/me?settings=true",
        json={"success": True, "data": {"theme": "dark"}},
    )
    result = runner.invoke(
        app, ["user", "settings", "--json"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code == 0
    assert "theme" in result.output


# --- Bug 3: torrents search removed ---


def test_torrents_search_command_removed() -> None:
    result = runner.invoke(
        app, ["torrents", "search", "ubuntu"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code != 0
    assert "No such command" in result.output or "Invalid value" in result.output


# --- Bug 4: general changelogs rss XML handling ---


def test_general_changelogs_rss_human_mode(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/changelogs/rss",
        text="<rss><channel><item>v1.0</item></channel></rss>",
    )
    result = runner.invoke(app, ["general", "changelogs", "--format", "rss"])
    assert result.exit_code == 0
    assert "<rss>" in result.output


# --- Bug 5: requestdl token param ---


def test_torrents_requestdl_includes_token(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/requestdl?torrent_id=1&file_id=2&token=dummy",
        json={"success": True, "data": {"link": "https://example.com"}},
    )
    result = runner.invoke(
        app,
        ["torrents", "requestdl", "1", "2", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0


def test_usenet_requestdl_includes_token(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/usenet/requestdl?usenet_id=1&file_id=2&token=dummy",
        json={"success": True, "data": {"link": "https://example.com"}},
    )
    result = runner.invoke(
        app,
        ["usenet", "requestdl", "1", "2", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0


# --- Bug 6: stream data token param ---


def test_stream_data_includes_token(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/stream/getstreamdata?presigned_token=xyz&token=dummy",
        json={"success": True, "data": {"url": "https://example.com"}},
    )
    result = runner.invoke(
        app, ["stream", "data", "xyz", "--json"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code == 0


# --- Bug 7: create commands --dry-run support ---


def test_torrents_create_dry_run() -> None:
    result = runner.invoke(
        app,
        [
            "torrents",
            "create",
            "--magnet",
            "magnet:?xt=urn:btih:abc",
            "--dry-run",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "POST /torrents/createtorrent" in result.output


def test_usenet_create_dry_run() -> None:
    result = runner.invoke(
        app,
        ["usenet", "create", "https://example.com/file.nzb", "--dry-run"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "POST /usenet/createusenetdownload" in result.output


def test_webdl_create_dry_run() -> None:
    result = runner.invoke(
        app,
        ["webdl", "create", "https://example.com/file.zip", "--dry-run"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "POST /webdl/createwebdownload" in result.output


def test_rss_create_dry_run() -> None:
    result = runner.invoke(
        app,
        [
            "rss",
            "create",
            "https://example.com/feed.xml",
            "--name",
            "Test Feed",
            "--dry-run",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "POST /rss/addrss" in result.output


def test_notifications_clear_dry_run() -> None:
    result = runner.invoke(
        app,
        ["notifications", "clear", "--dry-run"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "POST /notifications/clear" in result.output


# --- Bug 8: dry-run before confirmation prompt ---


def test_usenet_control_delete_dry_run_no_prompt() -> None:
    """--dry-run on a delete operation should not prompt for confirmation."""
    result = runner.invoke(
        app,
        ["usenet", "control", "10", "--operation", "delete", "--dry-run"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "Aborted" not in result.output


def test_webdl_control_delete_dry_run_no_prompt() -> None:
    result = runner.invoke(
        app,
        ["webdl", "control", "10", "--operation", "delete", "--dry-run"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "Aborted" not in result.output


def test_rss_delete_dry_run_no_prompt() -> None:
    result = runner.invoke(
        app,
        ["rss", "delete", "2", "--dry-run"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "Aborted" not in result.output


def test_queued_control_delete_dry_run_no_prompt() -> None:
    result = runner.invoke(
        app,
        ["queued", "control", "5", "delete", "--dry-run"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "Aborted" not in result.output


def test_integrations_cancel_dry_run_no_prompt() -> None:
    result = runner.invoke(
        app,
        ["integrations", "cancel", "job_xyz", "--dry-run"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "Aborted" not in result.output
