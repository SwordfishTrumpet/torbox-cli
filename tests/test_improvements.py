"""Tests for Future Improvement Backlog features implemented in this round."""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from torbox.cli import app
from torbox.commands._helpers import (
    confirm_destructive,
    validate_operation,
    validate_stream_type,
)
from torbox.formatters import print_dict_panel

runner = CliRunner()


# --- Config Doctor Tests ---


def test_config_doctor_human() -> None:
    result = runner.invoke(app, ["config", "doctor"], env={"TORBOX_API_KEY": "dummy"})
    assert result.exit_code == 0
    assert "Config Resolution Order" in result.output
    assert "Effective Values" in result.output


def test_config_doctor_json() -> None:
    result = runner.invoke(
        app, ["config", "doctor", "--json"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code == 0
    envelope = json.loads(result.output)
    assert envelope["success"] is True
    assert "sources" in envelope["data"]
    assert "effective" in envelope["data"]


# --- Operation Validation Tests ---


def test_validate_operation_accepted() -> None:
    assert validate_operation("delete") == "delete"
    assert validate_operation("PAUSE") == "pause"
    assert validate_operation("Resume") == "resume"


def test_validate_operation_rejected() -> None:
    with pytest.raises(Exception):
        validate_operation("invalid")


# --- Stream Type Validation Tests ---


def test_validate_stream_type_accepted() -> None:
    assert validate_stream_type("torrent") == "torrent"
    assert validate_stream_type("Usenet") == "usenet"
    assert validate_stream_type("WEBDOWNLOAD") == "webdownload"


def test_validate_stream_type_rejected() -> None:
    with pytest.raises(Exception):
        validate_stream_type("invalid")


# --- Confirmation Prompt Tests ---


def test_confirm_destructive_non_delete() -> None:
    assert confirm_destructive("pause", "torrent", 1, yes=False) is True


def test_confirm_destructive_yes_flag() -> None:
    assert confirm_destructive("delete", "torrent", 1, yes=True) is True


# --- Missing API Key Warning Test ---


def test_missing_api_key_warning(monkeypatch: Any, httpx_mock: Any) -> None:
    """Ensure a warning is emitted when no API key is available."""
    monkeypatch.delenv("TORBOX_API_KEY", raising=False)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = runner.invoke(app, ["torrents", "list"])
        assert result.exit_code != 0
        assert any("No API key configured" in str(warning.message) for warning in w)


# --- Auto-retry Flag Test ---


def test_auto_retry_flag_exists() -> None:
    result = runner.invoke(app, ["--auto-retry", "torrents", "list"])
    # Should fail because no API key, but flag should be accepted
    assert "No such option" not in result.output


# --- print_dict_panel Test ---


def test_print_dict_panel(capsys: Any) -> None:
    print_dict_panel({"name": "foo", "size": 123}, "Title")
    captured = capsys.readouterr()
    assert "name: foo" in captured.out
    assert "size: 123" in captured.out
    assert "Title" in captured.out


# --- Fixtures Tests ---


def test_fixtures_directory_exists() -> None:
    fixtures_dir = Path(__file__).parent / "fixtures"
    assert fixtures_dir.exists()
    assert (fixtures_dir / "torrents_list.json").exists()
    assert (fixtures_dir / "user_me.json").exists()


def test_torrents_fixture_loadable() -> None:
    fixture = Path(__file__).parent / "fixtures" / "torrents_list.json"
    data = json.loads(fixture.read_text())
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_user_me_fixture_loadable() -> None:
    fixture = Path(__file__).parent / "fixtures" / "user_me.json"
    data = json.loads(fixture.read_text())
    assert data["success"] is True
    assert data["data"]["email"] == "user@example.com"
