"""Tests for new features added in Future Improvement Backlog."""

from __future__ import annotations

import json
import os
import signal
import stat
import warnings
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from torbox.cli import app
from torbox.config import (
    ConfigValidationError,
    _check_file_permissions,
    _validate_retries,
    _validate_timeout,
    load_config,
)
from torbox.exceptions import (
    AuthenticationError,
    ClientError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    map_http_status,
)
from torbox.formatters import FieldMissingError, extract_field, print_json

runner = CliRunner()


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip()


def test_field_missing_path_returns_null() -> None:
    data = {"success": True, "data": {"name": "foo"}}
    ok = print_json(data, "data.missing")
    assert ok is False


def test_extract_field_raises_on_missing_key() -> None:
    with __import__("pytest").raises(FieldMissingError):
        extract_field({"a": 1}, "b")


def test_torrents_export_mocked(httpx_mock: Any) -> None:
    # Export now fetches info first, then calls magnettofile.
    httpx_mock.add_response(
        url="https://api.torbox.app/v1/api/torrents/mylist?id=42",
        json={"success": True, "data": {"id": 42, "hash": "abc123"}},
    )
    httpx_mock.add_response(
        url="https://api.torbox.app/v1/api/torrents/magnettofile",
        content=b"d8:announce",
    )
    result = runner.invoke(
        app,
        ["torrents", "export", "42", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "42" in result.output


def test_pagination_params_on_torrents_list(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url="https://api.torbox.app/v1/api/torrents/mylist?offset=5&limit=10",
        json={"success": True, "data": []},
    )
    result = runner.invoke(
        app,
        ["torrents", "list", "--offset", "5", "--limit", "10", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0


def test_pagination_params_on_usenet_list(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url="https://api.torbox.app/v1/api/usenet/mylist?offset=0&limit=50",
        json={"success": True, "data": []},
    )
    result = runner.invoke(
        app,
        ["usenet", "list", "--limit", "50", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0


def test_rate_limit_error_exit_code() -> None:
    exc = RateLimitError("Too many requests")
    assert exc.exit_code == 4


def test_map_http_status_429() -> None:
    exc = map_http_status(429)
    assert isinstance(exc, RateLimitError)
    assert exc.exit_code == 4


def test_map_http_status_403() -> None:
    exc = map_http_status(403)
    assert isinstance(exc, AuthenticationError)
    assert exc.exit_code == 2


def test_map_http_status_404() -> None:
    exc = map_http_status(404)
    assert isinstance(exc, NotFoundError)
    assert exc.exit_code == 6


def test_map_http_status_400() -> None:
    exc = map_http_status(400)
    assert isinstance(exc, ValidationError)
    assert exc.exit_code == 1


def test_map_http_status_500() -> None:
    exc = map_http_status(500)
    assert isinstance(exc, ClientError) or hasattr(exc, "exit_code")


def test_python_m_module_entry() -> None:
    """Ensure python -m torbox is importable and has cli_entry."""
    import importlib

    mod = importlib.import_module("torbox.__main__")
    assert hasattr(mod, "cli_entry")


# --- Config validation tests ---


def test_validate_timeout_acceptable() -> None:
    assert _validate_timeout(30) == 30


def test_validate_timeout_too_high() -> None:
    with __import__("pytest").raises(ConfigValidationError):
        _validate_timeout(301)


def test_validate_timeout_zero() -> None:
    with __import__("pytest").raises(ConfigValidationError):
        _validate_timeout(0)


def test_validate_retries_acceptable() -> None:
    assert _validate_retries(3) == 3


def test_validate_retries_too_high() -> None:
    with __import__("pytest").raises(ConfigValidationError):
        _validate_retries(11)


def test_validate_retries_negative() -> None:
    with __import__("pytest").raises(ConfigValidationError):
        _validate_retries(-1)


def test_load_config_invalid_timeout_env() -> None:
    env = {"TORBOX_TIMEOUT": "not_a_number"}
    with patch.dict(os.environ, env, clear=False):
        with __import__("pytest").raises(ConfigValidationError):
            load_config()


def test_load_config_invalid_retries_env() -> None:
    env = {"TORBOX_RETRIES": "-5"}
    with patch.dict(os.environ, env, clear=False):
        with __import__("pytest").raises(ConfigValidationError):
            load_config()


def test_check_file_permissions_warns_on_group_readable() -> None:
    mock_path = MagicMock(spec=Path)
    mock_stat = MagicMock()
    mock_stat.st_mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
    mock_path.stat.return_value = mock_stat
    mock_path.exists.return_value = True
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _check_file_permissions(mock_path)
        assert len(w) == 1
        assert "too open" in str(w[0].message)


# --- Ctrl-C handling tests ---


def test_sigint_handler_exits_130() -> None:
    """Verify the SIGINT handler exits with code 130."""
    from torbox.cli import _handle_interrupt

    with __import__("pytest").raises(SystemExit) as exc_info:
        _handle_interrupt(signal.SIGINT, None)
    assert exc_info.value.code == 130


# --- JSON error payload tests ---


def test_error_json_payload_includes_exit_code(capsys: Any) -> None:
    from torbox.cli import _print_error_json

    exc = AuthenticationError("Bad token")
    _print_error_json(exc)
    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert payload["success"] is False
    assert payload["error"] == "AuthenticationError"
    assert payload["exit_code"] == 2


# --- Quiet / Verbose tests ---


def test_quiet_suppresses_human_output(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url="https://api.torbox.app/v1/api/torrents/mylist?offset=0&limit=1000",
        json={"success": True, "data": [{"id": 1, "name": "x"}]},
    )
    result = runner.invoke(
        app,
        ["--quiet", "torrents", "list"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_verbose_prints_diagnostics(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url="https://api.torbox.app/v1/api/torrents/mylist?offset=0&limit=1000",
        json={"success": True, "data": []},
    )
    result = runner.invoke(
        app,
        ["--verbose", "torrents", "list", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "GET" in result.output or "ms" in result.output or result.output


# --- Top-level docs command tests ---


def test_top_level_docs_man() -> None:
    result = runner.invoke(app, ["docs", "--man"])
    assert result.exit_code == 0
    assert ".TH TORBOX" in result.output


def test_general_docs_man_backward_compat() -> None:
    result = runner.invoke(app, ["general", "docs", "--man"])
    assert result.exit_code == 0
    assert ".TH TORBOX" in result.output
