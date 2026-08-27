"""Tests for API audit fixes.

Covers file upload, auth, RSS expansion, and usenet formdata.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tests.conftest import strip_ansi
from torbox.cli import app
from torbox.client import TorBoxClient
from torbox.config import DEFAULT_BASE_URL
from torbox.exceptions import AuthenticationError

runner = CliRunner()


# --- Torrents create file upload ---


def test_torrents_create_with_file_multipart(httpx_mock: Any, tmp_path: Path) -> None:
    torrent_file = tmp_path / "test.torrent"
    torrent_file.write_bytes(b"d8:announce\x00e")
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/createtorrent",
        json={"success": True, "data": {"id": 1}},
    )
    result = runner.invoke(
        app,
        [
            "torrents",
            "create",
            "--file",
            str(torrent_file),
            "--name",
            "My File Torrent",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    content_type = requests[0].headers.get("content-type", "")
    assert "multipart/form-data" in content_type
    # httpx multipart bodies are complex; assert file field is present
    assert b'Content-Disposition: form-data; name="file"' in requests[0].content


def test_torrents_create_file_not_found() -> None:
    result = runner.invoke(
        app,
        ["torrents", "create", "--file", "/nonexistent/file.torrent"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code != 0
    assert "File not found" in result.output


def test_torrents_create_requires_magnet_or_file() -> None:
    result = runner.invoke(
        app,
        ["torrents", "create", "--name", "No Source"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code != 0
    assert "Either --magnet or --file is required" in strip_ansi(result.output)


# --- Torrents export using get_bytes ---


def test_torrents_export_uses_post_bytes(httpx_mock: Any) -> None:
    # Export now fetches info first, then calls magnettofile.
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/mylist?id=42",
        json={"success": True, "data": {"id": 42, "hash": "abc123"}},
    )
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/magnettofile",
        content=b"d8:announce\x00e",
    )
    result = runner.invoke(
        app,
        ["torrents", "export", "42", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["data"]["data"]["id"] == 42
    assert data["data"]["data"]["size"] == 13


# --- User auth-device-start without API key ---


def test_user_auth_device_start_no_api_key(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/auth/device/start?app=Third+Party+App",
        json={"success": True, "data": {"code": "123456"}},
    )
    # Explicitly clear API key env
    result = runner.invoke(app, ["user", "auth-device-start", "--json"])
    assert result.exit_code == 0
    assert "123456" in result.output


# --- Usenet create formdata ---


def test_usenet_create_uses_formdata(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/usenet/createusenetdownload",
        json={"success": True, "data": {"id": 1}},
    )
    result = runner.invoke(
        app,
        [
            "usenet",
            "create",
            "https://example.com/file.nzb",
            "--name",
            "My NZB",
            "--password",
            "secret",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    content_type = requests[0].headers.get("content-type", "")
    assert content_type.startswith("application/x-www-form-urlencoded")
    body = requests[0].content.decode()
    assert "link=https%3A%2F%2Fexample.com%2Ffile.nzb" in body
    assert "name=My+NZB" in body
    assert "password=secret" in body


# --- RSS create with all fields ---


def test_rss_create_with_all_fields(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/rss/addrss",
        json={"success": True, "data": {"id": 1}},
    )
    result = runner.invoke(
        app,
        [
            "rss",
            "create",
            "https://example.com/feed.xml",
            "--name",
            "My Feed",
            "--do-regex",
            ".*",
            "--dont-regex",
            "exclude",
            "--scan-interval",
            "60",
            "--dont-older-than",
            "7",
            "--type",
            "torrent",
            "--torrent-seeding",
            "2",
            "--pass-check",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    body = json.loads(requests[0].content)
    assert body["url"] == "https://example.com/feed.xml"
    assert body["name"] == "My Feed"
    assert body["do_regex"] == ".*"
    assert body["dont_regex"] == "exclude"
    assert body["scan_interval"] == 60
    assert body["dont_older_than"] == 7
    assert body["rss_type"] == "torrent"
    assert body["torrent_seeding"] == 2
    assert body["pass_check"] is True


# --- RSS edit with all fields ---


def test_rss_edit_with_all_fields(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/rss/modifyrss",
        json={"success": True, "data": {"id": 2}},
    )
    result = runner.invoke(
        app,
        [
            "rss",
            "edit",
            "2",
            "--name",
            "Updated",
            "--do-regex",
            "^.*$",
            "--dont-regex",
            "bad",
            "--scan-interval",
            "30",
            "--dont-older-than",
            "3",
            "--type",
            "usenet",
            "--torrent-seeding",
            "1",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    body = json.loads(requests[0].content)
    assert body["rss_feed_id"] == 2
    assert body["name"] == "Updated"
    assert body["do_regex"] == "^.*$"
    assert body["dont_regex"] == "bad"
    assert body["scan_interval"] == 30
    assert body["dont_older_than"] == 3
    assert body["rss_type"] == "usenet"
    assert body["torrent_seeding"] == 1


# --- Client get_bytes ---


def test_client_get_bytes(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/test/bytes",
        content=b"raw-bytes",
    )
    client = TorBoxClient(api_key="dummy")
    resp = client.get_bytes("/test/bytes")
    assert resp.content == b"raw-bytes"
    client.close()


def test_client_post_bytes(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/test/bytes",
        content=b"raw-post-bytes",
    )
    client = TorBoxClient(api_key="dummy")
    resp = client.post_bytes("/test/bytes", json={"magnet": "test"})
    assert resp.content == b"raw-post-bytes"
    client.close()


def test_client_get_bytes_no_auth(monkeypatch: Any, tmp_path: Any) -> None:
    monkeypatch.delenv("TORBOX_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # Avoid CWD .env supplying a real key
    client = TorBoxClient(api_key=None)
    assert client.api_key is None
    with pytest.warns(UserWarning, match="No API key configured"):
        with pytest.raises(AuthenticationError):
            client.get_bytes("/test/bytes")
    client.close()
