"""Tests: configuration validation errors must not escape as raw tracebacks.

Covers issue #26: `ConfigValidationError` was a plain `ValueError`, so it
escaped both `handle_errors()` and `cli_entry()` (which only caught
`TorBoxError`), surfacing as a Rich traceback that broke the JSON error
envelope contract in `--json` mode.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from typer.testing import CliRunner

from torbox.cli import app
from torbox.config import ConfigValidationError, load_config
from torbox.exceptions import TorBoxError

runner = CliRunner()
TEST_KEY = "dummy-test-key"


def test_config_validation_error_is_torbox_error() -> None:
    assert issubclass(ConfigValidationError, TorBoxError)
    exc = ConfigValidationError("Config file not found: /nope")
    assert exc.exit_code == 1


def test_bad_config_path_json_emits_envelope_no_traceback() -> None:
    result = runner.invoke(
        app,
        ["--config", "/nonexistent/config.env", "--json", "torrents", "list"],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "Traceback" not in result.stderr
    envelope = json.loads(result.stderr)
    assert envelope["success"] is False
    assert envelope["exit_code"] == 1
    assert "Config file not found" in envelope["detail"]


def test_bad_config_path_human_mode_no_traceback() -> None:
    result = runner.invoke(
        app,
        ["--config", "/nonexistent/config.env", "torrents", "list"],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "Traceback" not in result.stderr
    assert "Config file not found" in result.stderr


def test_invalid_timeout_json_emits_envelope_no_traceback() -> None:
    result = runner.invoke(
        app,
        ["torrents", "list", "--json"],
        env={"TORBOX_API_KEY": TEST_KEY, "TORBOX_TIMEOUT": "not_a_number"},
    )
    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "Traceback" not in result.stderr
    envelope = json.loads(result.stderr)
    assert envelope["success"] is False
    assert envelope["exit_code"] == 1
    assert "TORBOX_TIMEOUT" in envelope["detail"]


def test_invalid_retries_json_emits_envelope_no_traceback() -> None:
    result = runner.invoke(
        app,
        ["torrents", "list", "--json"],
        env={"TORBOX_API_KEY": TEST_KEY, "TORBOX_RETRIES": "-5"},
    )
    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "Traceback" not in result.stderr
    envelope = json.loads(result.stderr)
    assert envelope["success"] is False
    assert envelope["exit_code"] == 1
    assert "TORBOX_RETRIES" in envelope["detail"]


def test_config_doctor_bad_config_path_handled() -> None:
    result = runner.invoke(
        app,
        ["--config", "/nonexistent/config.env", "config", "doctor", "--json"],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "Traceback" not in result.stderr
    envelope = json.loads(result.stderr)
    assert envelope["success"] is False


def test_cli_entry_unexpected_exception_json_envelope(
    monkeypatch: Any, capsys: Any
) -> None:
    """Last-resort boundary: non-TorBoxError exceptions become JSON errors."""
    import torbox.cli as cli

    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("unexpected boom")

    monkeypatch.setattr(cli, "app", _boom)
    monkeypatch.setattr(cli.sys, "argv", ["torbox", "--json", "torrents", "list"])
    with pytest.raises(SystemExit) as excinfo:
        cli.cli_entry()
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    envelope = json.loads(captured.err)
    assert envelope["success"] is False
    assert envelope["error"] == "RuntimeError"
    assert "unexpected boom" in envelope["detail"]


def test_cli_entry_unexpected_exception_human_message(
    monkeypatch: Any, capsys: Any
) -> None:
    import torbox.cli as cli

    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("unexpected boom")

    monkeypatch.setattr(cli, "app", _boom)
    monkeypatch.setattr(cli.sys, "argv", ["torbox", "torrents", "list"])
    with pytest.raises(SystemExit) as excinfo:
        cli.cli_entry()
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    assert "unexpected boom" in captured.err


def test_cli_entry_typer_exit_propagates(monkeypatch: Any) -> None:
    """Normal typer.Exit flow control must not be swallowed by the boundary."""
    import typer as _typer

    import torbox.cli as cli

    def _exit(*args: Any, **kwargs: Any) -> Any:
        raise _typer.Exit(code=0)

    monkeypatch.setattr(cli, "app", _exit)
    monkeypatch.setattr(cli.sys, "argv", ["torbox", "torrents", "list"])
    with pytest.raises(_typer.Exit) as excinfo:
        cli.cli_entry()
    assert excinfo.value.exit_code == 0


def test_load_config_raises_typed_error_directly() -> None:
    with pytest.raises(ConfigValidationError):
        load_config(config_path="/nonexistent/config.env")
