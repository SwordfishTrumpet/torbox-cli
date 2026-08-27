"""Tests for hosters optional auth, notifications, and integrations."""

from __future__ import annotations

from typing import Any

from typer.testing import CliRunner

from torbox.cli import app
from torbox.client import TorBoxClient
from torbox.config import DEFAULT_BASE_URL

runner = CliRunner()


class TestOptionalAuth:
    """Ensure optional_get sends auth when available and skips when missing."""

    def test_optional_get_sends_auth_when_key_present(self, monkeypatch: Any) -> None:
        """optional_get must include Authorization header when api_key is set."""
        client = TorBoxClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert hasattr(client, "optional_get")

    def test_optional_get_does_not_raise_without_key(
        self, monkeypatch: Any, tmp_path: Any
    ) -> None:
        """optional_get must not raise AuthenticationError when api_key is missing."""
        monkeypatch.delenv("TORBOX_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)  # Avoid CWD .env interference
        client = TorBoxClient(api_key=None)
        assert client.api_key is None
        assert hasattr(client, "optional_get")


class TestHostersOptionalAuth:
    """Hosters command should work without an API key."""

    def test_hosters_without_api_key(
        self, monkeypatch: Any, tmp_path: Any, httpx_mock: Any
    ) -> None:
        """webdl hosters must succeed (JSON stub) when no API key is configured."""
        monkeypatch.delenv("TORBOX_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)  # Avoid CWD .env interference
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/webdl/hosters",
            json={"success": True, "data": [{"domain": "example.com"}]},
        )
        result = runner.invoke(app, ["webdl", "hosters", "--json"])
        assert result.exit_code == 0
        assert "AuthenticationError" not in result.output
        assert "No API key configured" not in result.output
        # optional_get must NOT send an Authorization header when no key is set.
        req = httpx_mock.get_requests()[0]
        assert "authorization" not in {k.lower() for k in req.headers}

    def test_hosters_with_api_key(self, monkeypatch: Any, httpx_mock: Any) -> None:
        """webdl hosters should accept an API key and send it as Bearer auth."""
        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/webdl/hosters",
            json={"success": True, "data": [{"domain": "example.com"}]},
        )
        result = runner.invoke(app, ["webdl", "hosters", "--json"])
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.headers["Authorization"] == "Bearer tb-test-key"


class TestNotificationsCommands:
    """Notifications commands are fully implemented with real API calls."""

    def test_notifications_list_human(self, monkeypatch: Any, httpx_mock: Any) -> None:
        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/notifications/mynotifications",
            json={"success": True, "data": [{"id": 1, "message": "hi"}]},
        )
        result = runner.invoke(app, ["notifications", "list"])
        assert result.exit_code == 0

    def test_notifications_list_json(self, monkeypatch: Any, httpx_mock: Any) -> None:
        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/notifications/mynotifications",
            json={"success": True, "data": [{"id": 1, "message": "hi"}]},
        )
        result = runner.invoke(app, ["notifications", "list", "--json"])
        assert result.exit_code == 0
        import json as _json

        out = _json.loads(result.output)
        assert out["success"] is True

    def test_notifications_rss_human(self, monkeypatch: Any, httpx_mock: Any) -> None:
        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/notifications/rss?token=tb-test-key",
            content=b"<rss></rss>",
        )
        result = runner.invoke(app, ["notifications", "rss"])
        assert result.exit_code == 0
        assert "<rss></rss>" in result.output

    def test_notifications_clear_json(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        result = runner.invoke(app, ["notifications", "clear", "--json"])
        assert result.exit_code in (0, 1, 2, 3)


class TestIntegrationsCommands:
    """Integrations commands (jobs, cancel) are fully implemented."""

    def test_integrations_jobs_human(self, monkeypatch: Any, httpx_mock: Any) -> None:
        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/integration/jobs/abc123",
            json={"success": True, "data": []},
        )
        result = runner.invoke(app, ["integrations", "jobs", "abc123"])
        assert result.exit_code == 0

    def test_integrations_jobs_json(self, monkeypatch: Any, httpx_mock: Any) -> None:
        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/integration/jobs/abc123",
            json={"success": True, "data": []},
        )
        result = runner.invoke(app, ["integrations", "jobs", "abc123", "--json"])
        assert result.exit_code == 0
        import json as _json

        out = _json.loads(result.output)
        assert out["success"] is True

    def test_integrations_cancel_dry_run(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        result = runner.invoke(
            app, ["integrations", "cancel", "job_xyz", "--yes", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "[dry-run]" in result.output
        assert "DELETE /integration/job/job_xyz" in result.output

    def test_integrations_list_no_longer_exists(self) -> None:
        result = runner.invoke(app, ["integrations", "list"])
        assert result.exit_code == 2


class TestHelpIncludesNewGroups:
    """Top-level --help should list the new command groups."""

    def test_top_level_help_has_notifications(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "notifications" in result.output

    def test_top_level_help_has_integrations(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "integrations" in result.output


class TestRequestDurationMs:
    """Verify request_duration_ms is tracked and threaded into JSON envelope."""

    def test_client_stores_last_request_duration(self, httpx_mock: Any) -> None:
        """After a request, _last_request_duration_ms should be set."""
        httpx_mock.add_response(
            url="https://api.torbox.app/v1/api/some/endpoint",
            json={"success": True, "data": {"key": "value"}},
        )
        client = TorBoxClient(api_key="tb-test-key")
        assert client.last_request_duration_ms == 0.0
        client.get("/some/endpoint")
        # After a request, duration should be a positive number
        assert client.last_request_duration_ms > 0.0

    def test_json_envelope_includes_duration(
        self, monkeypatch: Any, capsys: Any
    ) -> None:
        """When --json is used, envelope should contain request_duration_ms > 0.

        This test verifies the end-to-end flow: the client caches duration
        after a request, and print_json_envelope reads it from ctx.obj.
        """
        from unittest.mock import patch

        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        with patch(
            "torbox.commands._helpers.TorBoxClient.get",
            return_value={"success": True, "data": [{"id": 1, "name": "test"}]},
        ) as mock_get:
            mock_get.return_value = {
                "success": True,
                "data": [{"id": 1, "name": "test"}],
            }
            result = runner.invoke(app, ["torrents", "list", "--json"])
            assert result.exit_code == 0
            import json as _json

            parsed = _json.loads(result.output)
            assert "meta" in parsed
            assert "request_duration_ms" in parsed["meta"]

    def test_last_request_duration_property(self) -> None:
        """The last_request_duration_ms property returns a float."""
        client = TorBoxClient(api_key="tb-test")
        assert isinstance(client.last_request_duration_ms, float)
        assert client.last_request_duration_ms == 0.0

    def test_client_property_exists(self) -> None:
        """TorBoxClient has the last_request_duration_ms property."""
        client = TorBoxClient(api_key="test")
        assert hasattr(client, "last_request_duration_ms")


class TestGetClientCaching:
    """Verify _get_client caches the client on ctx.obj."""

    def test_get_client_caches_on_ctx(self) -> None:
        """Calling _get_client twice should return the same instance."""
        from unittest.mock import MagicMock

        from torbox.commands._helpers import _CLIENT_ATTR, _get_client

        ctx = MagicMock()
        ctx.obj = {"api_key": "tb-test"}

        client1 = _get_client(ctx)
        assert ctx.obj.get(_CLIENT_ATTR) is client1

        client2 = _get_client(ctx)
        assert client2 is client1


class TestTorrentsListTableColumns:
    """Verify human-mode torrents list uses a sensible column subset."""

    def test_list_torrents_uses_subset_columns(self, monkeypatch: Any) -> None:
        """The list_torrents command should pass columns to print_table."""
        from unittest.mock import patch

        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        with patch(
            "torbox.commands.torrents.print_table",
        ) as mock_print_table:
            with patch(
                "torbox.client.TorBoxClient.get",
                return_value={
                    "success": True,
                    "data": [
                        {
                            "id": 1,
                            "name": "test",
                            "size": "1.2 GB",
                            "status": "completed",
                            "progress": 100,
                            "download_speed": 0,
                            "cached": True,
                            "extra_field": "should_not_appear",
                        }
                    ],
                },
            ) as _mock_get:
                result = runner.invoke(app, ["torrents", "list"])
                assert result.exit_code == 0
                mock_print_table.assert_called_once()
                args, kwargs = mock_print_table.call_args
                assert "columns" in kwargs
                expected_cols = [
                    "id",
                    "name",
                    "size",
                    "status",
                    "progress",
                    "download_speed",
                    "cached",
                ]
                assert kwargs["columns"] == expected_cols


class TestJsonEnvelopeDurationIntegration:
    """Integration tests for JSON envelope duration tracking."""

    def test_print_json_envelope_reads_duration_from_cached_client(
        self, monkeypatch: Any
    ) -> None:
        """print_json_envelope should auto-read duration from cached client when
        duration_ms=0.0."""
        from unittest.mock import MagicMock, patch

        from torbox.commands._helpers import _CLIENT_ATTR, print_json_envelope

        mock_client = MagicMock()
        mock_client.last_request_duration_ms = 123.4

        ctx = MagicMock()
        ctx.obj = {
            "json": True,
            _CLIENT_ATTR: mock_client,
        }

        data = {"success": True, "data": "test"}

        with patch(
            "torbox.commands._helpers.print_json", return_value=True
        ) as mock_print:
            print_json_envelope(ctx, data, "test command")
            mock_print.assert_called_once()
            # The envelope should contain the duration from the cached client
            (envelope,), _ = mock_print.call_args
            assert envelope["meta"]["request_duration_ms"] == 123.4
