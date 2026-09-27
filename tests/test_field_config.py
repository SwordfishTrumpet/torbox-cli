"""Tests for field extraction and profile config."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import pytest

from torbox.config import (
    ConfigValidationError,
    _load_ini_profile,
    load_config,
)
from torbox.formatters import FieldMissingError, extract_field

# ---------------------------------------------------------------------------
# Field extraction tests (including verbose mode)
# ---------------------------------------------------------------------------


def test_extract_field_simple_key() -> None:
    data = {"name": "test", "id": 1}
    assert extract_field(data, "name") == "test"


def test_extract_field_nested() -> None:
    data = {"user": {"name": "alice"}}
    assert extract_field(data, "user.name") == "alice"


def test_extract_field_list_index() -> None:
    data = {"items": [{"id": 1}, {"id": 2}]}
    assert extract_field(data, "items.1.id") == 2


def test_extract_field_missing_key() -> None:
    data = {"a": 1}
    with pytest.raises(FieldMissingError, match="Key 'b' not found"):
        extract_field(data, "b")


def test_extract_field_index_out_of_range() -> None:
    data = [{"id": 1}]
    with pytest.raises(FieldMissingError, match="Index 5 out of range"):
        extract_field(data, "5")


def test_extract_field_cannot_traverse() -> None:
    data = {"a": "string"}
    with pytest.raises(FieldMissingError, match="Cannot traverse str"):
        extract_field(data, "a.b")


def test_extract_field_verbose_missing_key() -> None:
    data = {"a": 1}
    with pytest.raises(FieldMissingError) as exc_info:
        extract_field(data, "b", verbose=True)
    assert "traversed" in str(exc_info.value)


def test_extract_field_verbose_nested() -> None:
    data = {"x": {"y": 1}}
    with pytest.raises(FieldMissingError) as exc_info:
        extract_field(data, "x.z", verbose=True)
    assert "traversed" in str(exc_info.value)


def test_extract_field_available_keys() -> None:
    data = {"alpha": 1, "beta": 2}
    with pytest.raises(FieldMissingError) as exc_info:
        extract_field(data, "gamma")
    assert "available keys" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Profile config tests
# ---------------------------------------------------------------------------


def _clear_torbox_env() -> None:
    """Remove TorBox-related keys from os.environ."""
    for key in list(os.environ.keys()):
        if key.startswith("TORBOX_"):
            del os.environ[key]


def test_load_ini_profile_from_file() -> None:
    _clear_torbox_env()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("[default]\nTORBOX_API_KEY=key1\n")
        f.write("[work]\nTORBOX_API_KEY=key2\nTORBOX_TIMEOUT=60\n")
        path = Path(f.name)

    try:
        default = _load_ini_profile(path, "default")
        assert default.get("torbox_api_key") == "key1"

        work = _load_ini_profile(path, "work")
        assert work.get("torbox_api_key") == "key2"
        assert work.get("torbox_timeout") == "60"
    finally:
        path.unlink()
        _clear_torbox_env()


def test_load_ini_profile_missing_section() -> None:
    _clear_torbox_env()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("[default]\nTORBOX_API_KEY=key1\n")
        path = Path(f.name)

    try:
        result = _load_ini_profile(path, "missing")
        assert result == {}
    finally:
        path.unlink()
        _clear_torbox_env()


def test_load_config_with_profile(monkeypatch: Any, tmp_path: Path) -> None:
    _clear_torbox_env()
    monkeypatch.chdir(tmp_path)  # Avoid CWD .env interference
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("[default]\nTORBOX_API_KEY=default-key\n")
        f.write("[work]\nTORBOX_API_KEY=work-key\nTORBOX_TIMEOUT=60\n")
        path = Path(f.name)

    try:
        cfg = load_config(config_path=str(path), profile="work")
        assert cfg["api_key"] == "work-key"
        assert cfg["timeout"] == 60
    finally:
        path.unlink()
        _clear_torbox_env()


def test_load_config_profile_lowest_priority(monkeypatch: Any, tmp_path: Path) -> None:
    """Env var should override profile settings."""
    _clear_torbox_env()
    monkeypatch.chdir(tmp_path)  # Avoid CWD .env interference
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("[work]\nTORBOX_API_KEY=file-key\n")
        path = Path(f.name)

    old_key = os.environ.get("TORBOX_API_KEY")
    try:
        os.environ["TORBOX_API_KEY"] = "env-key"
        cfg = load_config(config_path=str(path), profile="work")
        assert cfg["api_key"] == "env-key"
    finally:
        if old_key is None:
            os.environ.pop("TORBOX_API_KEY", None)
        else:
            os.environ["TORBOX_API_KEY"] = old_key
        path.unlink()
        _clear_torbox_env()


def test_load_config_profile_invalid_timeout(monkeypatch: Any, tmp_path: Path) -> None:
    _clear_torbox_env()
    monkeypatch.chdir(tmp_path)  # Avoid CWD .env interference
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("[bad]\nTORBOX_TIMEOUT=not-a-number\n")
        path = Path(f.name)

    try:
        with pytest.raises(
            ConfigValidationError, match="TORBOX_TIMEOUT must be an integer"
        ):
            load_config(config_path=str(path), profile="bad")
    finally:
        path.unlink()
        _clear_torbox_env()


def test_load_config_profile_invalid_retries(monkeypatch: Any, tmp_path: Path) -> None:
    _clear_torbox_env()
    monkeypatch.chdir(tmp_path)  # Avoid CWD .env interference
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("[bad]\nTORBOX_RETRIES=999\n")
        path = Path(f.name)

    try:
        with pytest.raises(
            ConfigValidationError, match="TORBOX_RETRIES must be between"
        ):
            load_config(config_path=str(path), profile="bad")
    finally:
        path.unlink()
        _clear_torbox_env()


# ---------------------------------------------------------------------------
# Config doctor with profile
# ---------------------------------------------------------------------------


def test_config_doctor_shows_profile() -> None:
    _clear_torbox_env()
    from typer.testing import CliRunner

    from torbox.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["--profile", "work", "config", "doctor", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["effective"]["profile"] == "work"
    _clear_torbox_env()


# ---------------------------------------------------------------------------
# CLI --api-key override: it wins for the key only (issue #38)
# ---------------------------------------------------------------------------


def test_api_key_override_keeps_env_settings(monkeypatch: Any, tmp_path: Path) -> None:
    """A CLI key must not discard the configured base url, timeout and retries."""
    _clear_torbox_env()
    monkeypatch.chdir(tmp_path)  # Avoid CWD .env interference
    monkeypatch.setenv("TORBOX_BASE_URL", "https://mirror.example/v1/api")
    monkeypatch.setenv("TORBOX_TIMEOUT", "99")
    monkeypatch.setenv("TORBOX_RETRIES", "7")

    cfg = load_config(api_key_override="cli-key")

    assert cfg["api_key"] == "cli-key"
    assert cfg["base_url"] == "https://mirror.example/v1/api"
    assert cfg["timeout"] == 99
    assert cfg["retries"] == 7
    _clear_torbox_env()


def test_api_key_override_still_reads_the_config_file_and_profile(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Supplying a key must not skip the file merge or the profile section."""
    _clear_torbox_env()
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "config.env"
    config_file.write_text(
        "[work]\nTORBOX_API_KEY=profile-key\n"
        "TORBOX_BASE_URL=https://profile.example/v1/api\nTORBOX_TIMEOUT=45\n",
        encoding="utf-8",
    )

    cfg = load_config(
        api_key_override="cli-key", config_path=str(config_file), profile="work"
    )

    assert cfg["api_key"] == "cli-key"
    assert cfg["base_url"] == "https://profile.example/v1/api"
    assert cfg["timeout"] == 45
    _clear_torbox_env()


def test_api_key_override_wins_over_env_and_profile(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Precedence stays CLI flag > env var > .env/config file > profile."""
    _clear_torbox_env()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TORBOX_API_KEY", "env-key")
    config_file = tmp_path / "config.env"
    config_file.write_text("[work]\nTORBOX_API_KEY=profile-key\n", encoding="utf-8")

    cfg = load_config(
        api_key_override="cli-key", config_path=str(config_file), profile="work"
    )

    assert cfg["api_key"] == "cli-key"
    _clear_torbox_env()

    # Without the override, the env var still wins over the profile.
    monkeypatch.setenv("TORBOX_API_KEY", "env-key")
    cfg = load_config(config_path=str(config_file), profile="work")
    assert cfg["api_key"] == "env-key"
    _clear_torbox_env()


def test_cli_api_key_flag_uses_the_configured_base_url(
    monkeypatch: Any, tmp_path: Path, httpx_mock: Any
) -> None:
    """End-to-end: `--api-key` no longer redirects traffic to the default host."""
    _clear_torbox_env()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TORBOX_BASE_URL", "https://mirror.example/v1/api")
    httpx_mock.add_response(
        url=re.compile(r"https://mirror\.example/v1/api/torrents/mylist"),
        json={"success": True, "data": []},
    )

    from typer.testing import CliRunner

    from torbox.cli import app

    result = CliRunner().invoke(
        app, ["--api-key", "cli-key", "torrents", "list", "--json"], env={}
    )

    assert result.exit_code == 0, result.output
    request = httpx_mock.get_requests()[0]
    assert request.url.host == "mirror.example"
    assert request.url.path == "/v1/api/torrents/mylist"
    _clear_torbox_env()
