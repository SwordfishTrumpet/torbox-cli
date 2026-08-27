"""Security regression tests: --dry-run must never print credential material.

Covers issue #24: `dry_run_guard()` printed request payloads verbatim,
leaking OAuth tokens / passwords / session tokens to stdout. Redaction is
implemented centrally in `dry_run_guard()` so every call site is protected.
"""

from __future__ import annotations

from typer.testing import CliRunner

from torbox.cli import app
from torbox.commands._helpers import _is_secret_key, redact_secrets

runner = CliRunner()
TEST_KEY = "dummy-test-key"

SECRET_SAMPLE = "FAKE-SECRET-TOKEN-123"


# =============================================================================
# Unit tests for the redaction helper
# =============================================================================


def test_is_secret_key_recognizes_token_variants() -> None:
    for key in (
        "token",
        "refresh_token",
        "google_token",
        "onedrive_token",
        "gofile_token",
        "onefichier_token",
        "dropbox_token",
        "discord_token",
        "session_token",
        "password",
        "api_key",
        "apikey",
        "secret",
        "authorization",
    ):
        assert _is_secret_key(key), f"{key!r} should be treated as secret"


def test_is_secret_key_ignores_benign_keys() -> None:
    for key in (
        "file_id",
        "zip_link",
        "name",
        "magnet",
        "link",
        "tags",
        "alternative_hashes",
        "airlocked",
        "confirmation_code",
        "referral_code",
        "user_email",
        "vendor_name",
        "vendor_url",
        "torrent_id",
        "usenet_download_id",
        "webdl_id",
        "rss_feed_id",
        "operation",
    ):
        assert not _is_secret_key(key), f"{key!r} should not be treated as secret"


def test_redact_secrets_replaces_values() -> None:
    payload = {
        "file_id": 42,
        "google_token": SECRET_SAMPLE,
        "nested": {"refresh_token": "abc", "name": "keep"},
        "items": [{"token": "xyz"}, 1, "plain"],
    }
    redacted = redact_secrets(payload)
    assert redacted["file_id"] == 42
    assert redacted["google_token"] == "<redacted>"
    assert redacted["nested"]["refresh_token"] == "<redacted>"
    assert redacted["nested"]["name"] == "keep"
    assert redacted["items"][0]["token"] == "<redacted>"
    assert redacted["items"][1] == 1
    assert redacted["items"][2] == "plain"
    # Original payload must not be mutated.
    assert payload["google_token"] == SECRET_SAMPLE
    assert SECRET_SAMPLE not in repr(redacted)


# =============================================================================
# CLI-level regression tests: token values must not appear in --dry-run output
# =============================================================================


def test_integrations_upload_dry_run_redacts_tokens() -> None:
    result = runner.invoke(
        app,
        [
            "integrations",
            "upload",
            "googledrive",
            "42",
            "--token",
            SECRET_SAMPLE,
            "--dry-run",
        ],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0
    assert "[dry-run] POST /integration/googledrive" in result.output
    assert SECRET_SAMPLE not in result.output
    assert "<redacted>" in result.output


def test_integrations_oauth_register_dry_run_redacts_tokens() -> None:
    result = runner.invoke(
        app,
        [
            "integrations",
            "oauth",
            "register",
            "dropbox",
            "--token",
            SECRET_SAMPLE,
            "--refresh-token",
            "FAKE-REFRESH-456",
            "--dry-run",
        ],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0
    assert SECRET_SAMPLE not in result.output
    assert "FAKE-REFRESH-456" not in result.output
    assert "<redacted>" in result.output


def test_integrations_oauth_discord_linked_roles_dry_run_redacts() -> None:
    result = runner.invoke(
        app,
        [
            "integrations",
            "oauth",
            "discord-linked-roles",
            "--discord-token",
            SECRET_SAMPLE,
            "--dry-run",
        ],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0
    assert SECRET_SAMPLE not in result.output
    assert "<redacted>" in result.output


def test_user_refresh_token_dry_run_redacts_session_token() -> None:
    result = runner.invoke(
        app,
        ["user", "refresh-token", "session_FAKE_SECRET", "--dry-run"],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0
    assert "session_FAKE_SECRET" not in result.output
    assert "<redacted>" in result.output


def test_usenet_create_dry_run_redacts_password() -> None:
    result = runner.invoke(
        app,
        [
            "usenet",
            "create",
            "https://example.com/file.nzb",
            "--password",
            "p4ssw0rd-SECRET",
            "--dry-run",
        ],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0
    assert "p4ssw0rd-SECRET" not in result.output
    assert "<redacted>" in result.output


def test_dry_run_still_shows_non_secret_payload_values() -> None:
    """Redaction must not hide the information --dry-run exists to show."""
    result = runner.invoke(
        app,
        [
            "integrations",
            "upload",
            "googledrive",
            "42",
            "--token",
            SECRET_SAMPLE,
            "--dry-run",
        ],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0
    assert "42" in result.output  # file_id still visible
    assert "googledrive" in result.output
