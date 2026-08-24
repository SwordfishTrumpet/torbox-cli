"""Tests for API parity audit — new commands added 2026-05-18."""

from __future__ import annotations

import json
from typing import Any

from typer.testing import CliRunner

from torbox.cli import app
from torbox.config import DEFAULT_BASE_URL, DEFAULT_SERVER_URL

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


class TestUsenetAsyncCreate:
    def test_async_create_link(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/usenet/asynccreateusenetdownload",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["usenet", "async-create", "https://example.com/file.nzb", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "POST"
        body = req.content.decode()
        assert "link=https%3A%2F%2Fexample.com%2Ffile.nzb" in body

    def test_async_create_with_options(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/usenet/asynccreateusenetdownload",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            [
                "usenet",
                "async-create",
                "https://example.com/file.nzb",
                "--name",
                "My NZB",
                "--password",
                "secret",
                "--post-processing",
                "3",
                "--as-queued",
                "--add-only-if-cached",
                "--json",
            ],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        body = httpx_mock.get_requests()[0].content.decode()
        assert "name=My+NZB" in body
        assert "password=secret" in body
        assert "post_processing=3" in body
        assert "as_queued=1" in body
        assert "add_only_if_cached=1" in body

    def test_async_create_file(self, httpx_mock: Any, tmp_path: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/usenet/asynccreateusenetdownload",
            json={"success": True, "data": None},
        )
        nzb = tmp_path / "test.nzb"
        nzb.write_bytes(b"<nzb></nzb>")
        result = runner.invoke(
            app,
            ["usenet", "async-create", "--file", str(nzb), "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "POST"
        assert 'filename="test.nzb"' in req.content.decode()

    def test_async_create_no_source_fails(self) -> None:
        result = runner.invoke(
            app,
            ["usenet", "async-create"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code != 0


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

    def test_edit_with_airlocked(self, httpx_mock: Any) -> None:
        """--airlocked should be sent in payload when set."""
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/torrents/edittorrent",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["torrents", "edit", "42", "--name", "Test", "--airlocked"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["airlocked"] is True

    def test_edit_without_airlocked_not_in_payload(self, httpx_mock: Any) -> None:
        """Without --airlocked, the key should not appear in payload."""
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/torrents/edittorrent",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["torrents", "edit", "42", "--name", "Test"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert "airlocked" not in body

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

    def test_edit_with_airlocked(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/usenet/editusenetdownload",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["usenet", "edit", "5", "--name", "Test", "--airlocked"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["airlocked"] is True

    def test_edit_without_airlocked_not_in_payload(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/usenet/editusenetdownload",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["usenet", "edit", "5", "--name", "Test"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert "airlocked" not in body

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

    def test_checkcached_get_uses_query_params(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/usenet/checkcached?hash=hash1%2Chash2",
            json={"success": True, "data": {}},
        )
        result = runner.invoke(
            app,
            ["usenet", "checkcached", "hash1", "hash2", "--get", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "GET"
        assert "hash=hash1%2Chash2" in str(req.url)

    def test_checkcached_get_with_format_and_list_files(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=(
                f"{DEFAULT_BASE_URL}/usenet/checkcached"
                "?hash=hash1&format=object&list_files=1"
            ),
            json={"success": True, "data": {}},
        )
        result = runner.invoke(
            app,
            [
                "usenet",
                "checkcached",
                "hash1",
                "--get",
                "--format",
                "object",
                "--list-files",
                "--json",
            ],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "GET"
        assert "format=object" in str(req.url)
        assert "list_files=1" in str(req.url)


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

    def test_checkcached_batch_uses_post(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/webdl/checkcached",
            json={"success": True, "data": {}},
        )
        result = runner.invoke(
            app,
            [
                "webdl",
                "checkcached",
                "md5hash1",
                "md5hash2",
                "--batch",
                "--json",
            ],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "POST"
        body = json.loads(req.content)
        assert body["hashes"] == ["md5hash1", "md5hash2"]

    def test_checkcached_batch_with_format_and_list_files(
        self, httpx_mock: Any
    ) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/webdl/checkcached?format=list&list_files=1",
            json={"success": True, "data": {}},
        )
        result = runner.invoke(
            app,
            [
                "webdl",
                "checkcached",
                "abc123",
                "--batch",
                "--format",
                "list",
                "--list-files",
                "--json",
            ],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "POST"
        assert "format=list" in str(req.url)
        assert "list_files=1" in str(req.url)


class TestWebdlEdit:
    def test_edit_basic(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/webdl/editwebdownload",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["webdl", "edit", "5", "--name", "My Download"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["webdl_id"] == 5
        assert body["name"] == "My Download"

    def test_edit_with_airlocked(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/webdl/editwebdownload",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["webdl", "edit", "5", "--name", "Test", "--airlocked"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["airlocked"] is True

    def test_edit_without_airlocked_not_in_payload(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/webdl/editwebdownload",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["webdl", "edit", "5", "--name", "Test"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert "airlocked" not in body

    def test_edit_dry_run(self) -> None:
        result = runner.invoke(
            app,
            ["webdl", "edit", "5", "--name", "Test", "--dry-run"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        assert "[dry-run]" in result.output

    def test_edit_airlocked_dry_run(self) -> None:
        """airlocked should appear in dry-run payload."""
        result = runner.invoke(
            app,
            ["webdl", "edit", "5", "--name", "Test", "--airlocked", "--dry-run"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        assert "airlocked" in result.output


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


class TestNntp:
    def test_credentials(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/usenet/provider/account",
            json={"success": True, "data": {"username": "user", "password": "pass"}},
        )
        result = runner.invoke(
            app,
            ["nntp", "credentials", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["success"] is True
        assert out["data"]["data"]["username"] == "user"

    def test_reset_password(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/usenet/provider/account/resetpw",
            json={"success": True, "data": {"password": "newpass"}},
        )
        result = runner.invoke(
            app,
            ["nntp", "reset-password", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "POST"
        out = json.loads(result.output)
        assert out["success"] is True

    def test_nntp_help(self) -> None:
        result = runner.invoke(app, ["nntp", "--help"])
        assert result.exit_code == 0
        assert "credentials" in result.output
        assert "reset-password" in result.output

    def test_top_level_help_has_nntp(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "nntp" in result.output


class TestIntegrationsInfo:
    def test_info(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/integration/job/job_123",
            json={
                "success": True,
                "data": {"job_id": "job_123", "status": "completed"},
            },
        )
        result = runner.invoke(
            app,
            ["integrations", "info", "job_123", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["success"] is True
        assert out["data"]["data"]["job_id"] == "job_123"

    def test_info_dry_run(self) -> None:
        result = runner.invoke(
            app,
            ["integrations", "info", "job_123", "--dry-run"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        assert "[dry-run]" in result.output

    def test_integrations_help_includes_info(self) -> None:
        result = runner.invoke(app, ["integrations", "--help"])
        assert result.exit_code == 0
        assert "info" in result.output


class TestNotificationsClearOne:
    def test_clear_one(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/notifications/clear/42",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["notifications", "clear-one", "42", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "POST"
        out = json.loads(result.output)
        assert out["success"] is True

    def test_clear_one_dry_run(self) -> None:
        result = runner.invoke(
            app,
            ["notifications", "clear-one", "42", "--dry-run"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        assert "[dry-run]" in result.output

    def test_notifications_help_includes_clear_one(self) -> None:
        result = runner.invoke(app, ["notifications", "--help"])
        assert result.exit_code == 0
        assert "clear-one" in result.output


class TestTorrentsTorrentInfo:
    def test_torrentinfo_get(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/torrents/torrentinfo?hash=abc123",
            json={"success": True, "data": {"name": "Test Torrent", "size": 1000}},
        )
        result = runner.invoke(
            app,
            ["torrents", "torrentinfo", "abc123", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["success"] is True

    def test_torrentinfo_post_magnet(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/torrents/torrentinfo",
            json={"success": True, "data": {"name": "Magnet Torrent"}},
        )
        result = runner.invoke(
            app,
            ["torrents", "torrentinfo", "--magnet", "magnet:?xt=urn:btih:abc"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "POST"

    def test_torrentinfo_dry_run(self) -> None:
        result = runner.invoke(
            app,
            ["torrents", "torrentinfo", "abc123", "--dry-run"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        assert "[dry-run]" in result.output

    def test_torrents_help_includes_torrentinfo(self) -> None:
        result = runner.invoke(app, ["torrents", "--help"])
        assert result.exit_code == 0
        assert "torrentinfo" in result.output


class TestTorrentsExportData:
    def test_exportdata_magnet_json(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=(
                f"{DEFAULT_BASE_URL}/torrents/exportdata"
                "?torrent_id=42&type=magnet"
            ),
            json={
                "success": True,
                "data": "magnet:?xt=urn:btih:abc123",
            },
        )
        result = runner.invoke(
            app,
            ["torrents", "exportdata", "42", "--type", "magnet", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "GET"
        assert "torrent_id=42" in str(req.url)
        assert "type=magnet" in str(req.url)
        out = json.loads(result.output)
        assert out["data"]["data"] == "magnet:?xt=urn:btih:abc123"

    def test_exportdata_file_writes_bytes(
        self, httpx_mock: Any, tmp_path: Any
    ) -> None:
        httpx_mock.add_response(
            url=(
                f"{DEFAULT_BASE_URL}/torrents/exportdata"
                "?torrent_id=42&type=file"
            ),
            content=b"\x00torrent-data",
            headers={"content-type": "application/x-bittorrent"},
        )
        out_path = tmp_path / "movie.torrent"
        result = runner.invoke(
            app,
            [
                "torrents",
                "exportdata",
                "42",
                "--type",
                "file",
                "--output",
                str(out_path),
            ],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        assert out_path.read_bytes() == b"\x00torrent-data"

    def test_exportdata_invalid_type(self) -> None:
        result = runner.invoke(
            app,
            ["torrents", "exportdata", "42", "--type", "bogus"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code != 0
        assert "must be one of: magnet, file" in result.output


class TestIntegrationsUpload:
    def test_upload_googledrive(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/integration/googledrive",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["integrations", "upload", "googledrive", "42", "--token", "gtoken"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["file_id"] == 42
        assert body["google_token"] == "gtoken"

    def test_upload_pixeldrain(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/integration/pixeldrain",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["integrations", "upload", "pixeldrain", "42"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["file_id"] == 42

    def test_upload_dropbox(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/integration/dropbox",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["integrations", "upload", "dropbox", "42", "--dropbox-token", "dbtoken"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["file_id"] == 42
        assert body["dropbox_token"] == "dbtoken"

    def test_upload_onedrive(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/integration/onedrive",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["integrations", "upload", "onedrive", "42", "--token", "otoken"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["file_id"] == 42
        assert body["onedrive_token"] == "otoken"

    def test_upload_gofile(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/integration/gofile",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["integrations", "upload", "gofile", "42", "--gofile-token", "gftoken"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["file_id"] == 42
        assert body["gofile_token"] == "gftoken"

    def test_upload_1fichier(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/integration/1fichier",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["integrations", "upload", "1fichier", "42"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["file_id"] == 42

    def test_upload_invalid_provider(self) -> None:
        result = runner.invoke(
            app,
            ["integrations", "upload", "invalid", "42"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code != 0

    def test_upload_dry_run(self) -> None:
        result = runner.invoke(
            app,
            ["integrations", "upload", "googledrive", "42", "--dry-run"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        assert "[dry-run]" in result.output

    def test_list_jobs(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/integration/jobs",
            json={"success": True, "data": [{"job_id": "j1", "status": "running"}]},
        )
        result = runner.invoke(
            app,
            ["integrations", "list-jobs", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["success"] is True

    def test_integrations_help_includes_upload(self) -> None:
        result = runner.invoke(app, ["integrations", "--help"])
        assert result.exit_code == 0
        assert "upload" in result.output
        assert "list-jobs" in result.output


class TestUserSubscriptions:
    def test_subscriptions(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/user/subscriptions",
            json={"success": True, "data": [{"plan": "pro", "expires_at": None}]},
        )
        result = runner.invoke(
            app,
            ["user", "subscriptions", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["data"]["data"][0]["plan"] == "pro"


class TestUserStats:
    def test_stats(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/user/stats",
            json={"success": True, "data": {"total_downloads": 10}},
        )
        result = runner.invoke(
            app, ["user", "stats", "--json"], env={"TORBOX_API_KEY": "dummy"}
        )
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["success"] is True

    def test_stats_with_flags(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=(
                f"{DEFAULT_BASE_URL}/user/stats"
                "?general=true&bandwidth=true&bandwidth_grouping=true"
            ),
            json={"success": True, "data": {}},
        )
        result = runner.invoke(
            app,
            [
                "user",
                "stats",
                "--general",
                "--bandwidth",
                "--bandwidth-grouping",
                "--json",
            ],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert "general=true" in str(req.url)
        assert "bandwidth=true" in str(req.url)
        assert "bandwidth_grouping=true" in str(req.url)


class TestUserReferralData:
    def test_referral_data(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/user/referraldata",
            json={
                "success": True,
                "data": {"referred_accounts": 3, "purchases": 5},
            },
        )
        result = runner.invoke(
            app,
            ["user", "referral-data", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["data"]["data"]["referred_accounts"] == 3


class TestUserRefreshToken:
    def test_refresh_token(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/user/refreshtoken",
            json={"success": True, "data": {"token": "new-token"}},
        )
        result = runner.invoke(
            app,
            ["user", "refresh-token", "session_abc"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["session_token"] == "session_abc"

    def test_refresh_token_dry_run(self) -> None:
        result = runner.invoke(
            app,
            ["user", "refresh-token", "session_abc", "--dry-run"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        assert "[dry-run]" in result.output

    def test_user_help_includes_refresh_token(self) -> None:
        result = runner.invoke(app, ["user", "--help"])
        assert result.exit_code == 0
        assert "refresh-token" in result.output


class TestUserAddReferral:
    def test_add_referral(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/user/addreferral",
            json={"success": True, "data": None},
        )
        result = runner.invoke(
            app,
            ["user", "add-referral", "REFERRAL123"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body["referral_code"] == "REFERRAL123"

    def test_add_referral_dry_run(self) -> None:
        result = runner.invoke(
            app,
            ["user", "add-referral", "REFERRAL123", "--dry-run"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        assert "[dry-run]" in result.output

    def test_user_help_includes_add_referral(self) -> None:
        result = runner.invoke(app, ["user", "--help"])
        assert result.exit_code == 0
        assert "add-referral" in result.output


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


class TestGeneralStats30Days:
    def test_stats_30days(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/stats/30days",
            json={"success": True, "data": {"total_downloads": 12345}},
        )
        result = runner.invoke(app, ["general", "stats-30days", "--json"])
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "GET"
        assert "Authorization" not in req.headers
        out = json.loads(result.output)
        assert out["data"]["data"]["total_downloads"] == 12345


class TestGeneralPing:
    def test_ping(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=DEFAULT_SERVER_URL,
            json={"success": True, "data": {"status": "up"}},
        )
        result = runner.invoke(
            app,
            ["general", "ping", "--json"],
        )
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["success"] is True

    def test_general_help_includes_ping(self) -> None:
        result = runner.invoke(app, ["general", "--help"])
        assert result.exit_code == 0
        assert "ping" in result.output
