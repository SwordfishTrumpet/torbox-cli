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


# --- CRIT-1: Bulk delete confirmation ---


def test_torrents_control_all_delete_prompts_without_yes() -> None:
    """--all --operation delete without --yes should abort (no API call)."""
    result = runner.invoke(
        app,
        ["torrents", "control", "--operation", "delete", "--all"],
        env={"TORBOX_API_KEY": "dummy"},
        input="n\n",
    )
    assert result.exit_code == 0


def test_torrents_control_all_delete_proceeds_with_yes(httpx_mock: Any) -> None:
    """--all --operation delete with --yes should skip prompt and proceed."""
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/controltorrent",
        json={"success": True},
    )
    result = runner.invoke(
        app,
        ["torrents", "control", "--operation", "delete", "--all", "--yes"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert len(httpx_mock.get_requests()) == 1


def test_usenet_control_all_delete_prompts_without_yes() -> None:
    """--all --operation delete without --yes should abort."""
    result = runner.invoke(
        app,
        ["usenet", "control", "--operation", "delete", "--all"],
        env={"TORBOX_API_KEY": "dummy"},
        input="n\n",
    )
    assert result.exit_code == 0


def test_webdl_control_all_delete_prompts_without_yes() -> None:
    """--all --operation delete without --yes should abort."""
    result = runner.invoke(
        app,
        ["webdl", "control", "--operation", "delete", "--all"],
        env={"TORBOX_API_KEY": "dummy"},
        input="n\n",
    )
    assert result.exit_code == 0


# --- CRIT-2: Malformed --body raises clean error ---


def test_user_settings_malformed_body_error() -> None:
    """Malformed JSON in --body should produce exit_code=1, not a traceback."""
    result = runner.invoke(
        app,
        ["user", "settings", "--body", '{"theme":}', "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 1


# --- CRIT-5: user transaction-pdf ---


def test_user_transaction_pdf_json_mode(httpx_mock: Any) -> None:
    """transaction-pdf in JSON mode should return metadata envelope."""
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/transaction/pdf?transaction_id=123",
        content=b"%PDF-1.4 fake content",
    )
    result = runner.invoke(
        app,
        ["user", "transaction-pdf", "123", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "transaction_id" in result.output
    assert "size" in result.output


def test_user_transaction_pdf_output_file(httpx_mock: Any, tmp_path: Any) -> None:
    """transaction-pdf with --output should write bytes to file."""
    pdf_content = b"%PDF-1.4 fake pdf data"
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/transaction/pdf?transaction_id=42",
        content=pdf_content,
    )
    outfile = tmp_path / "invoice.pdf"
    result = runner.invoke(
        app,
        ["user", "transaction-pdf", "42", "--output", str(outfile)],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert outfile.read_bytes() == pdf_content


# --- HIGH-2: 401 maps to AuthenticationError ---


def test_map_http_status_401() -> None:
    """HTTP 401 should map to AuthenticationError with exit_code=2."""
    from torbox.exceptions import AuthenticationError, map_http_status

    exc = map_http_status(401)
    assert isinstance(exc, AuthenticationError)
    assert exc.exit_code == 2


# --- HIGH-3: Missing --config file raises error ---


def test_missing_config_file_raises_error() -> None:
    """Passing --config to a non-existent file should fail cleanly."""
    result = runner.invoke(
        app,
        ["--config", "/nonexistent/path.env", "general", "status", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code != 0


# --- HIGH-1: Genre filtering with string genres ---


def test_genre_filter_string_genres() -> None:
    """Genre filter should work when meta has genre as a string, not a list."""
    from unittest.mock import patch

    from torbox.commands.search import _resolve_to_imdb

    metas = [
        {"id": "tt001", "name": "Action Movie", "genre": "Action"},
        {"id": "tt002", "name": "Drama Movie", "genre": "Drama"},
    ]
    mock_result = {"metas": metas}

    with patch(
        "torbox.commands.search.StremioClient.cinemeta_search", return_value=mock_result
    ):
        result = _resolve_to_imdb("test", "movie", first=True, genre="Action")
        assert result == "tt001"

        result2 = _resolve_to_imdb("test", "movie", first=True, genre="Drama")
        assert result2 == "tt002"

        result3 = _resolve_to_imdb(
            "test", "movie", first=True, quiet=True, genre="Horror"
        )
        assert result3 is None
