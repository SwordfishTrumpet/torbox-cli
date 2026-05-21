"""Tests for API parity audit — new commands added 2026-05-18."""

from __future__ import annotations

import json
from typing import Any

from typer.testing import CliRunner

from torbox.cli import app
from torbox.config import DEFAULT_BASE_URL

runner = CliRunner()


class TestTorrentsAsyncCreate:
    def test_async_create_magnet(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/torrents/asynccreatetorrent",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["torrents", "async-create", "--magnet", "magnet:?xt=urn:btih:abc"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["magnet"] == "magnet:?xt=urn:btih:abc"

    def test_async_create_with_options(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/torrents/asynccreatetorrent",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            [
                "torrents",
                "async-create",
                "--magnet",
                "magnet:?xt=urn:btih:xyz",
                "--name",
                "Test",
                "--seed",
                "2",
                "--as-queued",
                "--allow-zip",
            ],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["name"] == "Test"
        assert body["seed"] == 2
        assert body["as_queued"] == 1
        assert body["allow_zip"] == 1

    def test_async_create_no_source_fails(self) -> None:
        result = runner.invoke(
            app,
            ["torrents", "async-create"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code != 0

    def test_async_create_json_mode(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/torrents/asynccreatetorrent",
            json={"success": True, "data": {"queued": True}},
        )
        result = runner.invoke(
            app,
            [
                "torrents",
                "async-create",
                "--magnet",
                "magnet:?xt=urn:btih:abc",
                "--json",
            ],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["success"] is True


class TestTorrentsEdit:
    def test_edit_with_name(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/torrents/edittorrent",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["torrents", "edit", "42", "--name", "New Name"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["torrent_id"] == 42
        assert body["name"] == "New Name"

    def test_edit_with_tags(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/torrents/edittorrent",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["torrents", "edit", "10", "--tags", "linux,iso,ubuntu"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["tags"] == ["linux", "iso", "ubuntu"]

    def test_edit_dry_run(self) -> None:
        result = runner.invoke(
            app,
            ["torrents", "edit", "42", "--name", "Test", "--dry-run"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        assert "[dry-run]" in result.output
        assert "PUT /torrents/edittorrent" in result.output


class TestTorrentsCheckcachedBatch:
    def test_checkcached_batch_uses_post(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/torrents/checkcached",
            json={"success": True, "data": {}},
        )
        result = runner.invoke(
            app,
            ["torrents", "checkcached", "hash1", "hash2", "--batch", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "POST"
        body = json.loads(req.content)
        assert body["hashes"] == ["hash1", "hash2"]

    def test_checkcached_default_uses_get(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/torrents/checkcached?hash=hash1%2Chash2",
            json={"success": True, "data": {}},
        )
        result = runner.invoke(
            app,
            ["torrents", "checkcached", "hash1", "hash2", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "GET"


class TestUsenetEdit:
    def test_edit_basic(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/usenet/editusenetdownload",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["usenet", "edit", "5", "--name", "My Download"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["usenet_download_id"] == 5
        assert body["name"] == "My Download"

    def test_edit_dry_run(self) -> None:
        result = runner.invoke(
            app,
            ["usenet", "edit", "5", "--name", "Test", "--dry-run"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        assert "[dry-run]" in result.output


class TestUsenetCheckcached:
    def test_checkcached_basic(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/usenet/checkcached",
            json={"success": True, "data": {"hash1": True}},
        )
        result = runner.invoke(
            app,
            ["usenet", "checkcached", "hash1", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "POST"
        body = json.loads(req.content)
        assert body["hashes"] == ["hash1"]

    def test_checkcached_with_format(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/usenet/checkcached?format=object",
            json={"success": True, "data": {}},
        )
        result = runner.invoke(
            app,
            ["usenet", "checkcached", "hash1", "--format", "object", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0

    def test_checkcached_with_list_files(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/usenet/checkcached?list_files=1",
            json={"success": True, "data": {}},
        )
        result = runner.invoke(
            app,
            ["usenet", "checkcached", "hash1", "--list-files", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0


class TestWebdlCheckcached:
    def test_checkcached_basic(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/webdl/checkcached?hash=md5hash1%2Cmd5hash2",
            json={"success": True, "data": {}},
        )
        result = runner.invoke(
            app,
            ["webdl", "checkcached", "md5hash1", "md5hash2", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "GET"
        assert "hash=md5hash1" in str(req.url)

    def test_checkcached_with_format_and_list_files(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(json={"success": True, "data": {}})
        result = runner.invoke(
            app,
            [
                "webdl",
                "checkcached",
                "abc123",
                "--format",
                "list",
                "--list-files",
                "--json",
            ],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert "format=list" in str(req.url)
        assert "list_files=1" in str(req.url)


class TestNotifications:
    def test_list(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/notifications/mynotifications",
            json={"success": True, "data": [{"id": 1, "title": "Test"}]},
        )
        result = runner.invoke(
            app,
            ["notifications", "list", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["success"] is True

    def test_rss(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/notifications/rss?token=dummy",
            text="<rss><channel></channel></rss>",
        )
        result = runner.invoke(
            app,
            ["notifications", "rss"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        assert "<rss>" in result.output

    def test_test(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/notifications/test",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["notifications", "test", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0

    def test_clear_with_yes(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/notifications/clear",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["notifications", "clear", "--yes", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0

    def test_clear_prompt_denied(self, monkeypatch: Any) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "n")
        result = runner.invoke(
            app,
            ["notifications", "clear"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0


class TestIntegrations:
    def test_jobs(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/integration/jobs/abc123",
            json={
                "success": True,
                "data": [{"job_id": "j1", "status": "completed"}],
            },
        )
        result = runner.invoke(
            app,
            ["integrations", "jobs", "abc123", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["success"] is True

    def test_cancel_with_yes(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/integration/job/job_xyz",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["integrations", "cancel", "job_xyz", "--yes", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0

    def test_cancel_dry_run(self) -> None:
        result = runner.invoke(
            app,
            ["integrations", "cancel", "job_xyz", "--yes", "--dry-run"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        assert "[dry-run]" in result.output
        assert "DELETE /integration/job/job_xyz" in result.output


class TestSpeedtestParams:
    def test_speedtest_with_params(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(json={"success": True, "data": {"speed": 100}})
        result = runner.invoke(
            app,
            [
                "general",
                "speedtest",
                "--test-length",
                "short",
                "--region",
                "us",
                "--user-ip",
                "1.2.3.4",
                "--json",
            ],
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert "test_length=short" in str(req.url)
        assert "region=us" in str(req.url)
        assert "user_ip=1.2.3.4" in str(req.url)

    def test_speedtest_without_params(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/speedtest",
            json={"success": True, "data": {"speed": 200}},
        )
        result = runner.invoke(
            app,
            ["general", "speedtest", "--json"],
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert "test_length" not in str(req.url)
