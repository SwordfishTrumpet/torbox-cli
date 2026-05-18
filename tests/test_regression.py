"""Regression tests for error codes, exit codes, envelope shape, and compact mode."""

from __future__ import annotations

import json
from typing import Any

import pytest
from typer.testing import CliRunner

from torbox.cli import app
from torbox.exceptions import (
    AuthenticationError,
    ClientError,
    DownloadError,
    NotFoundError,
    PlanRestrictedError,
    RateLimitError,
    ServerError,
    ValidationError,
    map_error_code,
    map_http_status,
)
from torbox.formatters import format_envelope

runner = CliRunner()


# --- map_error_code regression tests for every Appendix A entry ---


@pytest.mark.parametrize(
    ("code", "exc_class", "exit_code"),
    [
        ("DATABASE_ERROR", ServerError, 3),
        ("UNKNOWN_ERROR", ServerError, 3),
        ("NO_AUTH", AuthenticationError, 2),
        ("BAD_TOKEN", AuthenticationError, 2),
        ("AUTH_ERROR", AuthenticationError, 2),
        ("INVALID_OPTION", ValidationError, 1),
        ("REDIRECT_ERROR", ServerError, 3),
        ("OAUTH_VERIFICATION_ERROR", AuthenticationError, 2),
        ("ENDPOINT_NOT_FOUND", NotFoundError, 6),
        ("ITEM_NOT_FOUND", NotFoundError, 6),
        ("PLAN_RESTRICTED_FEATURE", PlanRestrictedError, 5),
        ("DUPLICATE_ITEM", ValidationError, 1),
        ("BOZO_RSS_FEED", ValidationError, 1),
        ("TOO_MUCH_DATA", ValidationError, 1),
        ("DOWNLOAD_TOO_LARGE", ValidationError, 1),
        ("MISSING_REQUIRED_OPTION", ValidationError, 1),
        ("TOO_MANY_OPTIONS", ValidationError, 1),
        ("BOZO_TORRENT", ValidationError, 1),
        ("NO_SERVERS_AVAILABLE_ERROR", ServerError, 3),
        ("MONTHLY_LIMIT", PlanRestrictedError, 5),
        ("COOLDOWN_LIMIT", DownloadError, 3),
        ("ACTIVE_LIMIT", DownloadError, 3),
        ("DOWNLOAD_SERVER_ERROR", DownloadError, 3),
        ("BOZO_NZB", ValidationError, 1),
        ("SEARCH_ERROR", ServerError, 3),
        ("INVALID_DEVICE", AuthenticationError, 2),
        ("DIFF_ISSUE", ValidationError, 1),
        ("LINK_OFFLINE", ValidationError, 1),
        ("VENDOR_DISABLED", ValidationError, 1),
        ("BOZO_REGEX", ValidationError, 1),
        ("BAD_CONFIRMATION", ValidationError, 1),
        ("CONFIRMATION_EXPIRED", ValidationError, 1),
        ("BOZO_FILE", ValidationError, 1),
    ],
)
def test_map_error_code_regression(
    code: str, exc_class: type[Exception], exit_code: int
) -> None:
    """Every mapped error code must produce correct exception and exit code."""
    exc = map_error_code(code, "detail")
    assert isinstance(exc, exc_class)
    assert exc.exit_code == exit_code


def test_map_error_code_unknown_defaults_to_server_error() -> None:
    """Unmapped error codes should default to ServerError with exit code 3."""
    exc = map_error_code("SOME_UNKNOWN_CODE", "something broke")
    assert isinstance(exc, ServerError)
    assert exc.exit_code == 3


# --- map_http_status regression tests ---


@pytest.mark.parametrize(
    ("status", "exc_class", "exit_code"),
    [
        (429, RateLimitError, 4),
        (403, AuthenticationError, 2),
        (404, NotFoundError, 6),
        (400, ValidationError, 1),
        (500, ServerError, 3),
        (502, ServerError, 3),
        (503, ServerError, 3),
        (418, ClientError, 1),  # arbitrary status
    ],
)
def test_map_http_status_regression(
    status: int, exc_class: type[Exception], exit_code: int
) -> None:
    exc = map_http_status(status, "detail")
    assert isinstance(exc, exc_class)
    assert exc.exit_code == exit_code


# --- JSON envelope shape tests ---


def test_format_envelope_structure() -> None:
    envelope = format_envelope({"foo": "bar"}, "torrents list", duration_ms=123.4)
    assert envelope["success"] is True
    assert envelope["command"] == "torrents list"
    assert envelope["data"] == {"foo": "bar"}
    assert "timestamp" in envelope["meta"]
    assert envelope["meta"]["request_duration_ms"] == 123.4
    assert "error" not in envelope or envelope.get("error") is None


def test_format_envelope_error_case() -> None:
    envelope = format_envelope(
        None,
        "torrents list",
        success=False,
        error="BAD_TOKEN",
        detail="Invalid token",
        exit_code=2,
    )
    assert envelope["success"] is False
    assert envelope["error"] == "BAD_TOKEN"
    assert envelope["detail"] == "Invalid token"
    assert envelope["exit_code"] == 2


def test_general_status_json_envelope(httpx_mock: Any) -> None:
    httpx_mock.add_response(url="https://api.torbox.app/v1/api/", json={"status": "ok"})
    result = runner.invoke(app, ["general", "status", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["success"] is True
    assert parsed["command"] == "general status"
    assert parsed["data"] == {"status": "ok"}
    assert "meta" in parsed
    assert "timestamp" in parsed["meta"]
    assert "request_duration_ms" in parsed["meta"]


def test_torrents_list_json_envelope(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url="https://api.torbox.app/v1/api/torrents/mylist?offset=0&limit=1000",
        json={"success": True, "data": [{"id": 1, "name": "test"}]},
    )
    result = runner.invoke(
        app, ["torrents", "list", "--json"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["success"] is True
    assert parsed["command"] == "torrents list"
    assert parsed["data"]["success"] is True
    assert "meta" in parsed


# --- Compact JSON mode tests ---


def test_compact_json_single_line(httpx_mock: Any) -> None:
    httpx_mock.add_response(url="https://api.torbox.app/v1/api/", json={"status": "ok"})
    # Global --compact must come before subcommand in Typer/Click
    result = runner.invoke(app, ["--json", "--compact", "general", "status"])
    assert result.exit_code == 0
    output = result.output.strip()
    # Should be a single line (no newlines inside the JSON object)
    assert "\n" not in output
    parsed = json.loads(output)
    assert parsed["success"] is True


# --- Human error format tests ---


def test_human_error_contains_actionable_text(httpx_mock: Any) -> None:
    """When not in JSON mode, errors should be colored and actionable."""
    httpx_mock.add_response(url="https://api.torbox.app/v1/api/", status_code=403)
    result = runner.invoke(app, ["general", "status"])
    assert result.exit_code == 2
    stderr = result.output
    assert "Authentication failed" in stderr or "Error" in stderr


# --- Dry-run tests ---


def test_torrents_control_dry_run() -> None:
    result = runner.invoke(
        app,
        ["torrents", "control", "42", "--operation", "delete", "--dry-run"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "POST /torrents/controltorrent" in result.output


def test_usenet_control_dry_run() -> None:
    result = runner.invoke(
        app,
        ["usenet", "control", "10", "--operation", "pause", "--dry-run"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output


# --- Help examples presence ---


def test_help_examples_present() -> None:
    result = runner.invoke(app, ["torrents", "list", "--help"])
    assert result.exit_code == 0
    assert "Example:" in result.output


# --- Missing field path still returns null with exit code 1 ---


def test_field_missing_path_returns_null(httpx_mock: Any) -> None:
    httpx_mock.add_response(url="https://api.torbox.app/v1/api/", json={"status": "ok"})
    result = runner.invoke(
        app, ["general", "status", "--json", "--field", "missing.path"]
    )
    assert result.exit_code == 1
    assert result.output.strip() == "null"


# --- Manpage output structure tests ---


def test_manpage_output_structure() -> None:
    result = runner.invoke(app, ["docs", "--man"])
    assert result.exit_code == 0
    output = result.output
    assert ".TH TORBOX 1" in output
    assert ".SH NAME" in output
    assert output.count(".SH ") >= 1


def test_general_docs_man_backward_compat() -> None:
    result = runner.invoke(app, ["general", "docs", "--man"])
    assert result.exit_code == 0
    output = result.output
    assert ".TH TORBOX 1" in output
    assert ".SH NAME" in output
    assert output.count(".SH ") >= 1
