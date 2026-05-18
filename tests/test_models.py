"""Tests for model validation, field extraction, and profile config."""

from __future__ import annotations

import json
import os
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
from torbox.models import (
    CacheStatus,
    DeviceCodeAuth,
    Hoster,
    JSONEnvelope,
    QueuedDownload,
    RSSFeed,
    RSSFeedItem,
    StreamData,
    StreamMetadata,
    TorBoxResponse,
    Torrent,
    TorrentList,
    Transaction,
    UsenetDownload,
    User,
    UserSettings,
    WebDownload,
)

# ---------------------------------------------------------------------------
# Pydantic model validation
# ---------------------------------------------------------------------------


def test_torbox_response_minimal() -> None:
    resp = TorBoxResponse(success=True)
    assert resp.success is True
    assert resp.error is None
    assert resp.detail is None
    assert resp.data is None


def test_torbox_response_with_error() -> None:
    resp = TorBoxResponse(success=False, error="BAD_TOKEN", detail="Invalid token")
    assert resp.error == "BAD_TOKEN"
    assert resp.detail == "Invalid token"


def test_torrent_model() -> None:
    t = Torrent(id=1, hash="a" * 40, name="Test", size=1024, status="completed")
    assert t.id == 1
    assert t.name == "Test"


def test_torrent_partial_fields() -> None:
    """Partial data should work because all fields except id are optional."""
    t = Torrent(id=42, hash="b" * 40)
    assert t.name is None
    assert t.size is None


def test_torrent_list_model() -> None:
    tl = TorrentList(
        data=[Torrent(id=1, hash="a" * 40)],
        total=1,
        offset=0,
        limit=10,
    )
    assert len(tl.data) == 1
    assert tl.total == 1


def test_user_model() -> None:
    u = User(id=1, email="user@example.com", plan="pro")
    assert u.plan == "pro"


def test_user_settings_model() -> None:
    us = UserSettings(id=1, settings={"theme": "dark"})
    assert us.settings == {"theme": "dark"}


def test_usenet_download_model() -> None:
    ud = UsenetDownload(id=1, name="file.nzb", status="downloading")
    assert ud.nzb_url is None


def test_web_download_model() -> None:
    wd = WebDownload(id=1, link="https://example.com/file.zip")
    assert wd.hoster is None


def test_hoster_model() -> None:
    h = Hoster(id=1, name="example", enabled=True)
    assert h.enabled is True


def test_transaction_model() -> None:
    t = Transaction(id=1, type="purchase", amount=9.99, currency="USD")
    assert t.amount == 9.99


def test_rss_feed_model() -> None:
    rf = RSSFeed(id=1, url="https://example.com/feed.xml")
    assert rf.name is None


def test_rss_feed_item_model() -> None:
    rfi = RSSFeedItem(id=1, title="Episode 1", link="https://example.com/1")
    assert rfi.feed_id is None


def test_stream_metadata_model() -> None:
    sm = StreamMetadata(token="abc123", type="torrent", id=42)
    assert sm.file_id is None


def test_stream_data_model() -> None:
    sd = StreamData(
        token="abc123",
        streams=[{"url": "https://cdn.example.com/1"}],
        subtitles=[{"lang": "en"}],
    )
    assert sd.audio_tracks is None


def test_device_code_auth_model() -> None:
    dca = DeviceCodeAuth(
        device_code="dc123",
        code="uc456",
        verification_url="https://example.com/auth",
        friendly_verification_url="https://example.com/auth/friendly",
    )
    assert dca.interval is None
    assert dca.friendly_verification_url == "https://example.com/auth/friendly"


def test_cache_status_model() -> None:
    cs = CacheStatus(hash="a" * 40, cached=True)
    assert cs.files is None


def test_json_envelope_model() -> None:
    env = JSONEnvelope(
        success=True,
        command="torrents list",
        data=[{"id": 1}],
        meta={"timestamp": "2025-01-01T00:00:00Z"},
    )
    assert env.exit_code is None


def test_model_dump_json() -> None:
    t = Torrent(id=1, hash="a" * 40, name="Test")
    dumped = t.model_dump_json()
    parsed = json.loads(dumped)
    assert parsed["id"] == 1
    assert parsed["name"] == "Test"


# ---------------------------------------------------------------------------
# CamelCase alias compatibility tests
# ---------------------------------------------------------------------------


def test_user_model_validate_camelcase() -> None:
    u = User.model_validate(
        {
            "id": 1,
            "email": "user@example.com",
            "plan": "pro",
            "apiKey": "tb-1234",
        }
    )
    assert u.api_key == "tb-1234"


def test_usenet_download_model_validate_camelcase() -> None:
    ud = UsenetDownload.model_validate(
        {
            "id": 1,
            "name": "file.nzb",
            "nzbUrl": "https://example.com/file.nzb",
        }
    )
    assert ud.nzb_url == "https://example.com/file.nzb"


def test_transaction_model_validate_camelcase() -> None:
    t = Transaction.model_validate(
        {
            "id": 1,
            "type": "purchase",
            "amount": 9.99,
            "createdAt": "2024-01-01T00:00:00Z",
        }
    )
    assert t.created_at == "2024-01-01T00:00:00Z"


def test_rss_feed_model_validate_camelcase() -> None:
    rf = RSSFeed.model_validate(
        {
            "id": 1,
            "url": "https://example.com/feed.xml",
            "lastUpdated": "2024-06-15T12:00:00Z",
        }
    )
    assert rf.last_updated == "2024-06-15T12:00:00Z"


def test_stream_metadata_model_validate_camelcase() -> None:
    sm = StreamMetadata.model_validate(
        {
            "token": "abc123",
            "type": "torrent",
            "id": 42,
            "fileId": 7,
        }
    )
    assert sm.file_id == 7


def test_queued_download_model_validate_camelcase() -> None:
    qd = QueuedDownload.model_validate(
        {
            "id": 1,
            "name": "download",
            "createdAt": "2024-03-01T00:00:00Z",
        }
    )
    assert qd.created_at == "2024-03-01T00:00:00Z"


def test_model_populate_by_name_snake_case_still_works() -> None:
    u = User.model_validate({"id": 1, "email": "a@b.com", "api_key": "key1"})
    assert u.api_key == "key1"


# ---------------------------------------------------------------------------
# Malformed / partial response tests
# ---------------------------------------------------------------------------


def test_malformed_torrent_missing_required_id() -> None:
    """Missing required field 'id' should raise ValidationError."""
    with pytest.raises(Exception):
        Torrent(hash="a" * 40)  # type: ignore[call-arg]


def test_malformed_torrent_wrong_id_type() -> None:
    """Wrong type for id should raise ValidationError."""
    with pytest.raises(Exception):
        Torrent(id="not-an-int", hash="a" * 40)  # type: ignore[arg-type]


def test_partial_api_response_wrapped() -> None:
    """Simulate an API response missing optional fields."""
    raw: dict[str, Any] = {"success": True, "data": {"id": 1, "hash": "a" * 40}}
    resp = TorBoxResponse.model_validate(raw)
    assert resp.success is True
    assert resp.data == {"id": 1, "hash": "a" * 40}


def test_malformed_list_response() -> None:
    """Simulate a list response where 'data' is not a list."""
    raw: dict[str, Any] = {"data": "unexpected-string"}
    with pytest.raises(Exception):
        TorrentList.model_validate(raw)


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


def test_load_config_with_profile() -> None:
    _clear_torbox_env()
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


def test_load_config_profile_lowest_priority() -> None:
    """Env var should override profile settings."""
    _clear_torbox_env()
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


def test_load_config_profile_invalid_timeout() -> None:
    _clear_torbox_env()
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


def test_load_config_profile_invalid_retries() -> None:
    _clear_torbox_env()
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
