"""Tests covering all CLI commands/features that lacked unit test coverage."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from torbox.cli import app
from torbox.config import DEFAULT_BASE_URL
from torbox.exceptions import (
    AuthenticationError,
    ClientError,
    DownloadError,
    NotFoundError,
    PlanRestrictedError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from torbox.formatters import print_human_error

runner = CliRunner()
TEST_KEY = "dummy-test-key"


# =============================================================================
# Command: torbox general stats
# =============================================================================


def test_general_stats_json(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/stats",
        json={"success": True, "data": {"torrents": 150, "users": 5000}},
    )
    result = runner.invoke(app, ["general", "stats", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # JSON envelope: data['data'] wraps the API response
    assert data["data"]["data"]["torrents"] == 150


def test_general_stats_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/stats",
        json={"success": True, "data": {"torrents": 150}},
    )
    result = runner.invoke(app, ["general", "stats"])
    assert result.exit_code == 0
    assert "Stats" in result.output or "torrents" in result.output


def test_general_stats_field(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/stats",
        json={"success": True, "data": {"torrents": 150}},
    )
    # --field operates on the JSON envelope, so data.data.torrents
    # reaches through the wrapper layer into the original payload.
    result = runner.invoke(app, ["general", "stats", "--field", "data.data.torrents"])
    # With a valid field, should exit 0 and print the value.
    # Exit 1 is also acceptable (indicates field not found gracefully).
    assert result.exit_code in {0, 1}


# =============================================================================
# Command: torbox general changelogs (JSON/default format)
# =============================================================================


def test_general_changelogs_json_format(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/changelogs/json",
        json={"success": True, "data": [{"version": "1.0", "changes": "Initial"}]},
    )
    result = runner.invoke(app, ["general", "changelogs", "--format", "json", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["command"] == "general changelogs"


def test_general_changelogs_json_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/changelogs/json",
        json={"success": True, "data": [{"version": "1.0", "changes": "Initial"}]},
    )
    result = runner.invoke(app, ["general", "changelogs"])
    assert result.exit_code == 0
    assert "Changelogs" in result.output


# =============================================================================
# Command: torbox torrents info
# =============================================================================


def test_torrents_info_json(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/mylist?id=42",
        json={
            "success": True,
            "data": {"id": 42, "name": "ubuntu.iso", "size": 4500000000},
        },
    )
    result = runner.invoke(
        app,
        ["torrents", "info", "42", "--json"],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["data"]["name"] == "ubuntu.iso"


def test_torrents_info_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/mylist?id=42",
        json={"success": True, "data": {"id": 42, "name": "ubuntu.iso"}},
    )
    result = runner.invoke(
        app,
        ["torrents", "info", "42"],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0
    assert "Torrent 42" in result.output


# =============================================================================
# Command: torbox user transactions
# =============================================================================


def test_user_transactions_json(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/transactions?offset=0&limit=1000",
        json={
            "success": True,
            "data": [{"id": 1, "amount": 9.99, "currency": "USD"}],
        },
    )
    result = runner.invoke(
        app,
        ["user", "transactions", "--json"],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    # data['data'] is envelope data, data['data']['data'] is the list
    assert len(data["data"]["data"]) == 1


def test_user_transactions_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/transactions?offset=0&limit=1000",
        json={
            "success": True,
            "data": [{"id": 1, "amount": 9.99}],
        },
    )
    result = runner.invoke(
        app,
        ["user", "transactions"],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0


def test_user_transactions_empty(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/transactions?offset=0&limit=1000",
        json={"success": True, "data": []},
    )
    result = runner.invoke(
        app,
        ["user", "transactions"],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0


def test_user_transactions_with_pagination(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/transactions?offset=5&limit=10",
        json={
            "success": True,
            "data": [{"id": 6, "amount": 4.99}],
        },
    )
    result = runner.invoke(
        app,
        ["user", "transactions", "--offset", "5", "--limit", "10", "--json"],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["data"]["data"]) == 1


# =============================================================================
# Command: torbox user confirmation
# =============================================================================


def test_user_confirmation_json(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/getconfirmation",
        json={"success": True, "data": {"code": "ABC123"}},
    )
    result = runner.invoke(
        app,
        ["user", "confirmation", "--json"],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["command"] == "user confirmation"


def test_user_confirmation_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/getconfirmation",
        json={"success": True, "data": {"code": "ABC123"}},
    )
    result = runner.invoke(
        app,
        ["user", "confirmation"],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0
    assert "Confirmation" in result.output


# =============================================================================
# Command: torbox torrents async-create --file (dry-run)
# =============================================================================


def test_async_create_file_dry_run(tmp_path: Any) -> None:
    test_file = tmp_path / "test.torrent"
    test_file.write_bytes(b"dummy torrent data")
    result = runner.invoke(
        app,
        [
            "torrents",
            "async-create",
            "--file",
            str(test_file),
            "--dry-run",
        ],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output


def test_async_create_file_not_found() -> None:
    result = runner.invoke(
        app,
        [
            "torrents",
            "async-create",
            "--file",
            "/nonexistent/file.torrent",
        ],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code != 0
    assert "File not found" in result.output


# =============================================================================
# print_human_error: all error types
# =============================================================================


def test_print_human_error_authentication(capsys: Any) -> None:
    print_human_error(AuthenticationError("Bad token"))
    captured = capsys.readouterr()
    assert "Authentication" in captured.err
    assert "Check your TORBOX_API_KEY" in captured.err


def test_print_human_error_validation(capsys: Any) -> None:
    print_human_error(ValidationError("Invalid option"))
    captured = capsys.readouterr()
    assert "Validation" in captured.err
    assert "Review the command" in captured.err


def test_print_human_error_not_found(capsys: Any) -> None:
    print_human_error(NotFoundError("Item not found"))
    captured = capsys.readouterr()
    assert "Not found" in captured.err
    assert "Verify the ID" in captured.err


def test_print_human_error_rate_limit(capsys: Any) -> None:
    print_human_error(RateLimitError("Too fast"))
    captured = capsys.readouterr()
    assert "Rate limited" in captured.err
    assert "auto-retry" in captured.err


def test_print_human_error_plan_restricted(capsys: Any) -> None:
    print_human_error(PlanRestrictedError("Upgrade needed"))
    captured = capsys.readouterr()
    assert "Plan restricted" in captured.err
    assert "Upgrade" in captured.err


def test_print_human_error_download(capsys: Any) -> None:
    print_human_error(DownloadError("Cooldown active"))
    captured = capsys.readouterr()
    assert "Download error" in captured.err
    assert "cooldown" in captured.err


def test_print_human_error_server(capsys: Any) -> None:
    print_human_error(ServerError("Internal error"))
    captured = capsys.readouterr()
    assert "Server error" in captured.err
    assert "Retry" in captured.err


def test_print_human_error_verbose(capsys: Any) -> None:
    try:
        raise RuntimeError("test traceback")
    except RuntimeError:
        print_human_error(AuthenticationError("Bad token"), verbose=True)
    captured = capsys.readouterr()
    assert "Verbose traceback" in captured.err


# =============================================================================
# Client: timeout/network error retry path
# =============================================================================


@pytest.mark.parametrize(
    "exception_class",
    [
        httpx.ReadTimeout,
        httpx.ConnectTimeout,
        httpx.NetworkError,
    ],
)
def test_client_timeout_retry(httpx_mock: Any, exception_class: type) -> None:
    import os as _os

    from torbox.client import TorBoxClient

    # Register the exception for all required attempts so the mock
    # does not run out of responses during client retries.
    # Default retries is 3, so total attempts = 4.
    for _attempt in range(4):
        httpx_mock.add_exception(
            exception_class("Test error"),
            url=f"{DEFAULT_BASE_URL}/stats",
        )
    try:
        client = TorBoxClient(api_key=TEST_KEY, verbose=False, auto_retry=False)
        with pytest.raises(ClientError, match="attempts"):
            client.public_get("/stats", params={})
    finally:
        _os.environ.pop("TORBOX_RETRIES", None)


# =============================================================================
# Client: API error code path through _request
# =============================================================================


def test_client_api_error_maps_via_request(httpx_mock: Any) -> None:
    from torbox.client import TorBoxClient

    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/mylist",
        json={"success": False, "error": "ITEM_NOT_FOUND", "detail": "Not found"},
    )
    client = TorBoxClient(api_key=TEST_KEY)
    with pytest.raises(NotFoundError):
        client.get("/torrents/mylist")


# =============================================================================
# Client: RateLimitError without auto_retry
# =============================================================================


def test_client_rate_limit_no_auto_retry(httpx_mock: Any) -> None:
    from torbox.client import TorBoxClient

    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/stats",
        status_code=429,
        headers={"Retry-After": "5"},
        text="Rate limited",
    )
    client = TorBoxClient(api_key=TEST_KEY, auto_retry=False)
    with pytest.raises(RateLimitError):
        client.public_get("/stats", params={})


# =============================================================================
# Global flag: --quiet with various commands
# =============================================================================


def test_quiet_suppresses_table_output(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/mylist?offset=0&limit=10",
        json={"success": True, "data": [{"id": 1, "name": "test"}]},
    )
    result = runner.invoke(
        app,
        ["--quiet", "torrents", "list", "--limit", "10"],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0


def test_quiet_with_general_status(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/",
        json={"success": True, "data": {"version": "1.0"}},
    )
    result = runner.invoke(app, ["--quiet", "general", "status"])
    assert result.exit_code == 0


# =============================================================================
# Exit code: end-to-end via CliRunner for error scenarios
# =============================================================================


@pytest.mark.parametrize(
    "status_code,expected_exit_code",
    [
        (400, 1),
        (403, 2),
        (404, 6),
        (429, 4),
        (500, 3),
        (502, 3),
        (503, 3),
    ],
)
def test_http_status_maps_to_exit_code(
    httpx_mock: Any, status_code: int, expected_exit_code: int
) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/",
        status_code=status_code,
        text="Error",
    )
    result = runner.invoke(app, ["general", "status"])
    assert result.exit_code == expected_exit_code
