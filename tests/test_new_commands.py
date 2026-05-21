"""Tests for new commands added to fill API coverage gaps."""

from __future__ import annotations

import json
from typing import Any

from typer.testing import CliRunner

from torbox.cli import app
from torbox.config import DEFAULT_BASE_URL

runner = CliRunner()
TEST_KEY = "dummy-test-key"


# =============================================================================
# webdl requestdl
# =============================================================================


def test_webdl_requestdl_basic(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/webdl/requestdl?webdl_id=1&file_id=2&token=dummy",
        json={"success": True, "data": {"link": "https://example.com"}},
    )
    result = runner.invoke(
        app, ["webdl", "requestdl", "1", "2", "--json"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code == 0
    out = json.loads(result.output)
    assert out["success"] is True


def test_webdl_requestdl_with_flags(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=(
            f"{DEFAULT_BASE_URL}/webdl/requestdl"
            "?webdl_id=1&file_id=2&token=dummy&zip_link=1&user_ip=1.2.3.4&redirect=1&append_name=1"
        ),
        json={"success": True, "data": {"link": "https://example.com"}},
    )
    result = runner.invoke(
        app,
        [
            "webdl",
            "requestdl",
            "1",
            "2",
            "--zip-link",
            "--user-ip",
            "1.2.3.4",
            "--redirect",
            "--append-name",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0


# =============================================================================
# webdl async-create
# =============================================================================


def test_webdl_async_create_basic(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/webdl/asynccreatewebdownload",
        json={"success": True, "data": {"id": 1}},
    )
    result = runner.invoke(
        app,
        ["webdl", "async-create", "https://example.com/file.zip", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    req = httpx_mock.get_requests()[0]
    body = req.content.decode()
    assert "link=https%3A%2F%2Fexample.com%2Ffile.zip" in body


def test_webdl_async_create_with_options(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/webdl/asynccreatewebdownload",
        json={"success": True, "data": {"id": 1}},
    )
    result = runner.invoke(
        app,
        [
            "webdl",
            "async-create",
            "https://example.com/file.zip",
            "--name",
            "Test",
            "--password",
            "secret",
            "--as-queued",
            "--add-only-if-cached",
            "--allow-zip",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    req = httpx_mock.get_requests()[0]
    body = req.content.decode()
    assert "name=Test" in body
    assert "password=secret" in body
    assert "as_queued=1" in body
    assert "add_only_if_cached=1" in body
    assert "allow_zip=1" in body


def test_webdl_async_create_dry_run() -> None:
    result = runner.invoke(
        app,
        [
            "webdl",
            "async-create",
            "https://example.com/file.zip",
            "--dry-run",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output


# =============================================================================
# torrents files
# =============================================================================


def test_torrents_files_with_files(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/mylist?id=42",
        json={
            "success": True,
            "data": {
                "id": 42,
                "name": "test",
                "files": [
                    {"id": 1, "name": "a.mkv", "size": 1000},
                    {"id": 2, "name": "b.mkv", "size": 2000},
                ],
            },
        },
    )
    result = runner.invoke(
        app, ["torrents", "files", "42", "--json"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code == 0
    out = json.loads(result.output)
    assert out["success"] is True


def test_torrents_files_no_files(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/mylist?id=42",
        json={"success": True, "data": {"id": 42, "name": "test"}},
    )
    result = runner.invoke(
        app, ["torrents", "files", "42"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code == 0
    assert "No files listed" in result.output


# =============================================================================
# stream delete
# =============================================================================


def test_stream_delete_with_yes(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/stream/deletestream",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        ["stream", "delete", "abc123", "--yes", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    req = httpx_mock.get_requests()[0]
    assert req.method == "DELETE"
    body = json.loads(req.content)
    assert body["token"] == "abc123"


def test_stream_delete_dry_run() -> None:
    result = runner.invoke(
        app,
        ["stream", "delete", "abc123", "--yes", "--dry-run"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "DELETE /stream/deletestream" in result.output


def test_stream_delete_prompt_denied(monkeypatch: Any) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "n")
    result = runner.invoke(
        app,
        ["stream", "delete", "abc123"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0


# =============================================================================
# torrents export edge cases
# =============================================================================


def test_torrents_export_invalid_info(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/mylist?id=42",
        json={"success": True, "data": "invalid"},
    )
    result = runner.invoke(
        app, ["torrents", "export", "42", "--json"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code != 0
    assert "not found or invalid response" in result.output


def test_torrents_export_no_hash(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/mylist?id=42",
        json={"success": True, "data": {"id": 42, "name": "Test", "hash": ""}},
    )
    result = runner.invoke(
        app, ["torrents", "export", "42", "--json"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code != 0
    assert "no hash available" in result.output


def test_torrents_export_json(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/mylist?id=42",
        json={"success": True, "data": {"id": 42, "hash": "abc123"}},
    )
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/magnettofile",
        content=b"torrent\x00data",
    )
    result = runner.invoke(
        app, ["torrents", "export", "42", "--json"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code == 0
    out = json.loads(result.output)
    assert out["success"] is True
    assert out["data"]["data"]["hash"] == "abc123"


def test_torrents_export_to_file(httpx_mock: Any, tmp_path: Any) -> None:
    out_path = tmp_path / "test.torrent"
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/mylist?id=42",
        json={"success": True, "data": {"id": 42, "hash": "abc123"}},
    )
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/magnettofile",
        content=b"torrent\x00data",
    )
    result = runner.invoke(
        app,
        ["torrents", "export", "42", "--output", str(out_path)],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert out_path.read_bytes() == b"torrent\x00data"


# =============================================================================
# queued add
# =============================================================================


def test_queued_add_torrent(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/queued/addqueued",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        ["queued", "add", "torrent", "42", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    req = httpx_mock.get_requests()[0]
    body = json.loads(req.content)
    assert body["type"] == "torrent"
    assert body["id"] == 42


def test_queued_add_invalid_type() -> None:
    result = runner.invoke(
        app, ["queued", "add", "invalid", "42"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code != 0
    assert "BadParameter" in result.output or "must be one of" in result.output


def test_queued_add_dry_run() -> None:
    result = runner.invoke(
        app,
        ["queued", "add", "usenet", "10", "--dry-run"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output


# =============================================================================
# usenet export
# =============================================================================


def test_usenet_export_json(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/usenet/mylist?id=10",
        json={"success": True, "data": {"id": 10, "name": "Test"}},
    )
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/usenet/nzbtofile",
        content=b"<nzb></nzb>",
    )
    result = runner.invoke(
        app, ["usenet", "export", "10", "--json"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code == 0
    out = json.loads(result.output)
    assert out["success"] is True
    assert out["data"]["data"]["size"] == 11


def test_usenet_export_to_file(httpx_mock: Any, tmp_path: Any) -> None:
    out_path = tmp_path / "test.nzb"
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/usenet/mylist?id=10",
        json={"success": True, "data": {"id": 10, "name": "Test"}},
    )
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/usenet/nzbtofile",
        content=b"<nzb></nzb>",
    )
    result = runner.invoke(
        app,
        ["usenet", "export", "10", "--output", str(out_path)],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert out_path.read_bytes() == b"<nzb></nzb>"


def test_usenet_export_invalid_info(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/usenet/mylist?id=10",
        json={"success": True, "data": "invalid"},
    )
    result = runner.invoke(
        app, ["usenet", "export", "10", "--json"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code != 0
    assert "not found or invalid response" in result.output


# =============================================================================
# user auth-device-poll and auth-device-complete
# =============================================================================


def test_user_auth_device_poll(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/auth/device/poll?device_code=dc123",
        json={"success": True, "data": {"status": "pending"}},
    )
    result = runner.invoke(app, ["user", "auth-device-poll", "dc123", "--json"])
    assert result.exit_code == 0
    out = json.loads(result.output)
    assert out["success"] is True


def test_user_auth_device_complete(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/auth/device/complete",
        json={"success": True, "data": {"token": "tb-new-token"}},
    )
    result = runner.invoke(
        app,
        ["user", "auth-device-complete", "dc123", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    req = httpx_mock.get_requests()[0]
    body = json.loads(req.content)
    assert body["device_code"] == "dc123"
    out = json.loads(result.output)
    assert out["success"] is True


# =============================================================================
# Help presence for new commands
# =============================================================================


def test_webdl_help_includes_requestdl() -> None:
    result = runner.invoke(app, ["webdl", "--help"])
    assert result.exit_code == 0
    assert "requestdl" in result.output


def test_webdl_help_includes_async_create() -> None:
    result = runner.invoke(app, ["webdl", "--help"])
    assert result.exit_code == 0
    assert "async-create" in result.output


def test_torrents_help_includes_files() -> None:
    result = runner.invoke(app, ["torrents", "--help"])
    assert result.exit_code == 0
    assert "files" in result.output


def test_stream_help_includes_delete() -> None:
    result = runner.invoke(app, ["stream", "--help"])
    assert result.exit_code == 0
    assert "delete" in result.output


def test_queued_help_includes_add() -> None:
    result = runner.invoke(app, ["queued", "--help"])
    assert result.exit_code == 0
    assert "add" in result.output


def test_usenet_help_includes_export() -> None:
    result = runner.invoke(app, ["usenet", "--help"])
    assert result.exit_code == 0
    assert "export" in result.output


def test_user_help_includes_device_auth() -> None:
    result = runner.invoke(app, ["user", "--help"])
    assert result.exit_code == 0
    assert "auth-device-poll" in result.output
    assert "auth-device-complete" in result.output
