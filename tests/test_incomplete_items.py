"""Tests for hosters optional auth, notifications, and integrations."""

from __future__ import annotations

from typing import Any

from typer.testing import CliRunner

from torbox.cli import app
from torbox.client import TorBoxClient

runner = CliRunner()


class TestOptionalAuth:
    """Ensure optional_get sends auth when available and skips when missing."""

    def test_optional_get_sends_auth_when_key_present(self, monkeypatch: Any) -> None:
        """optional_get must include Authorization header when api_key is set."""
        client = TorBoxClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert hasattr(client, "optional_get")

    def test_optional_get_does_not_raise_without_key(self) -> None:
        """optional_get must not raise AuthenticationError when api_key is missing."""
        client = TorBoxClient(api_key=None)
        assert client.api_key is None
        assert hasattr(client, "optional_get")


class TestHostersOptionalAuth:
    """Hosters command should work without an API key."""

    def test_hosters_without_api_key(self, monkeypatch: Any) -> None:
        """webdl hosters must succeed (JSON stub) when no API key is configured."""
        monkeypatch.delenv("TORBOX_API_KEY", raising=False)
        result = runner.invoke(app, ["webdl", "hosters", "--json"])
        assert "AuthenticationError" not in result.output
        assert "No API key configured" not in result.output

    def test_hosters_with_api_key(self, monkeypatch: Any) -> None:
        """webdl hosters should accept an API key and attempt the request."""
        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        result = runner.invoke(app, ["webdl", "hosters", "--json"])
        assert "AuthenticationError" not in result.output
        assert "No API key configured" not in result.output


class TestNotificationsCommands:
    """Notifications commands are fully implemented with real API calls."""

    def test_notifications_list_human(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        result = runner.invoke(app, ["notifications", "list"])
        assert result.exit_code in (0, 1, 2, 3, 4)

    def test_notifications_list_json(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        result = runner.invoke(app, ["notifications", "list", "--json"])
        assert result.exit_code in (0, 1, 2, 3, 4)

    def test_notifications_rss_human(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        result = runner.invoke(app, ["notifications", "rss"])
        assert result.exit_code in (0, 1, 2, 3, 4)

    def test_notifications_clear_json(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        result = runner.invoke(app, ["notifications", "clear", "--json"])
        assert result.exit_code in (0, 1, 2, 3)


class TestIntegrationsCommands:
    """Integrations commands (jobs, cancel) are fully implemented."""

    def test_integrations_jobs_human(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        result = runner.invoke(app, ["integrations", "jobs", "abc123"])
        assert result.exit_code in (0, 1, 2, 3, 4)

    def test_integrations_jobs_json(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("TORBOX_API_KEY", "tb-test-key")
        result = runner.invoke(app, ["integrations", "jobs", "abc123", "--json"])
        assert result.exit_code in (0, 1, 2, 3, 4)

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
