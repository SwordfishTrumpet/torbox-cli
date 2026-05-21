"""Tests for API audit fixes.

Covers file upload, auth, RSS expansion, usenet formdata, and models.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from torbox.cli import app
from torbox.client import TorBoxClient
from torbox.config import DEFAULT_BASE_URL
from torbox.models import (
    DeviceCodeAuth,
    Hoster,
    RSSFeed,
    RSSFeedItem,
    SearchEngine,
    StreamData,
    StreamMetadata,
    UserSettings,
)

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
    assert "Either --magnet or --file is required" in result.output


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


# --- Model expansion tests ---


def test_hoster_full_fields() -> None:
    h = Hoster(
        id=1,
        name="example",
        enabled=True,
        domains=["example.com"],
        url="https://example.com",
        icon="icon.png",
        status=True,
        type="hoster",
        note="note",
        nsfw=False,
        daily_link_limit=100,
        daily_link_used=50,
        daily_bandwidth_limit=1000000,
        daily_bandwidth_used=500000,
        per_link_size_limit=1024,
        regex=".*",
    )
    assert h.domains == ["example.com"]
    assert h.daily_link_limit == 100


def test_rss_feed_full_fields() -> None:
    rf = RSSFeed(
        id=1,
        url="https://example.com/feed.xml",
        name="My Feed",
        enabled=True,
        lastUpdated="2024-01-01T00:00:00Z",
        createdAt="2024-01-01T00:00:00Z",
        lastChecked="2024-01-02T00:00:00Z",
        auth_id=42,
        source="rss",
        source_name="RSS Source",
        do_regex=".*",
        dont_regex="exclude",
        status=1,
        scan_interval=60,
        dont_older_than=7,
        status_message="OK",
        type="torrent",
        torrent_seeding=2,
        state="active",
    )
    assert rf.source_name == "RSS Source"
    assert rf.state == "active"


def test_rss_feed_item_full_fields() -> None:
    rfi = RSSFeedItem(
        id=1,
        title="Episode 1",
        link="https://example.com/1",
        published="2024-01-01",
        feed_id=7,
        createdAt="2024-01-01T00:00:00Z",
        rss_name="Feed Name",
        rss_url="https://example.com/feed.xml",
        ignored=False,
        downloaded=True,
        name="Episode 1",
        status="completed",
        status_message="Done",
        seed_torrents=True,
        type="torrent",
    )
    assert rfi.rss_name == "Feed Name"
    assert rfi.seed_torrents is True


def test_search_engine_full_fields() -> None:
    se = SearchEngine(
        id=1,
        name="Jackett",
        enabled=True,
        createdAt="2024-01-01T00:00:00Z",
        auth_id=42,
        type="jackett",
        url="https://jackett.example.com",
        apikey="secret",
        active=True,
        valid=True,
        download_type="torrent",
        indexers=["1337x", "RARBG"],
    )
    assert se.apikey == "secret"
    assert se.indexers == ["1337x", "RARBG"]


def test_stream_data_full_fields() -> None:
    sd = StreamData(
        token="abc",
        streams=[{"url": "https://cdn.example.com/1"}],
        subtitles=[{"lang": "en"}],
        audio_tracks=[{"lang": "en"}],
        resolutions=[{"width": 1920}],
        hls_url="https://hls.example.com",
        domain="cdn.example.com",
        presigned_token="ptok",
        subtitle_index=0,
        audio_index=1,
        resolution_index=2,
        file_token="ftok",
        is_transcoding=False,
        needs_transcoding=True,
        metadata=StreamMetadata(video={"codec": "h264"}),
        search_metadata={"title": "Movie"},
        intro_information={"start": 0, "end": 120},
        scrobbling_enabled=True,
    )
    assert sd.hls_url == "https://hls.example.com"
    assert sd.needs_transcoding is True
    assert sd.metadata is not None
    assert sd.metadata.video == {"codec": "h264"}


def test_stream_metadata_full_fields() -> None:
    sm = StreamMetadata(
        token="abc",
        type="torrent",
        id=42,
        fileId=7,
        urls=["https://cdn.example.com/1"],
        hls_url="https://hls.example.com",
        domain="cdn.example.com",
        presigned_token="ptok",
        subtitle_index=0,
        audio_index=1,
        resolution_index=2,
        file_token="ftok",
        is_transcoding=False,
        needs_transcoding=True,
        video={"codec": "h264", "width": 1920, "height": 1080, "frame_rate": 24},
        audios=[{"lang": "en"}],
        subtitles=[{"lang": "en"}],
        thumbnail="https://thumb.example.com",
        chapters=[{"start": 0, "end": 300}],
        search_metadata={"title": "Movie"},
        intro_information={"start": 0, "end": 120},
        scrobbling_enabled=True,
    )
    assert sm.video is not None
    assert sm.video["width"] == 1920
    assert sm.thumbnail == "https://thumb.example.com"


def test_device_code_auth_correct_fields() -> None:
    dca = DeviceCodeAuth(
        device_code="dc123",
        code="uc456",
        verification_url="https://example.com/auth",
        friendly_verification_url="https://example.com/auth/friendly",
        expires_at="2024-12-31T23:59:59Z",
        interval=5,
    )
    assert dca.code == "uc456"
    assert dca.verification_url == "https://example.com/auth"
    assert dca.friendly_verification_url == "https://example.com/auth/friendly"
    assert dca.expires_at == "2024-12-31T23:59:59Z"


def test_user_settings_full_fields() -> None:
    us = UserSettings(
        id=1,
        email="user@example.com",
        plan="pro",
        settings={"theme": "dark"},
        email_notifications=True,
        web_notifications=False,
        rss_notifications=True,
        discord_id="12345",
        discord_notifications=True,
        telegram_id="67890",
        webhook_url="https://hooks.example.com",
        seed_torrents=True,
        allow_zipped=False,
        google_drive_folder_id="abc123",
        mega_email="mega@example.com",
        mega_password="secret",
        cdn_selection="default",
        append_filename_to_links=True,
        dashboard_filter={"status": "completed"},
    )
    assert us.email_notifications is True
    assert us.dashboard_filter == {"status": "completed"}


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


def test_client_get_bytes_no_auth() -> None:
    client = TorBoxClient()
    with pytest.raises(Exception):
        client.get_bytes("/test/bytes")
    client.close()
