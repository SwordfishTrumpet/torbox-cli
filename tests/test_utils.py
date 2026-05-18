"""Tests for utility helpers."""

from __future__ import annotations

from datetime import datetime

from torbox.utils import format_size, is_valid_torrent_hash, parse_date, parse_size


def test_format_size_zero() -> None:
    assert format_size(0) == "0 B"


def test_format_size_bytes() -> None:
    assert format_size(512) == "512.0 B"


def test_format_size_kb() -> None:
    assert format_size(1024) == "1.0 KB"


def test_format_size_mb() -> None:
    assert format_size(1024 * 1024) == "1.0 MB"


def test_format_size_gb() -> None:
    assert format_size(1024 * 1024 * 1024) == "1.0 GB"


def test_format_size_tb() -> None:
    assert format_size(1024 * 1024 * 1024 * 1024) == "1.0 TB"


def test_parse_date_iso_with_microseconds() -> None:
    result = parse_date("2025-01-15T12:30:45.123456Z")
    assert result == datetime(2025, 1, 15, 12, 30, 45, 123456)


def test_parse_date_iso_without_microseconds() -> None:
    result = parse_date("2025-01-15T12:30:45Z")
    assert result == datetime(2025, 1, 15, 12, 30, 45)


def test_parse_date_space_format() -> None:
    result = parse_date("2025-01-15 12:30:45")
    assert result == datetime(2025, 1, 15, 12, 30, 45)


def test_parse_date_invalid() -> None:
    assert parse_date("not-a-date") is None


def test_is_valid_torrent_hash_valid() -> None:
    assert is_valid_torrent_hash("a" * 40) is True
    assert is_valid_torrent_hash("A1B2C3D4E5F6" + "0" * 28) is True


def test_is_valid_torrent_hash_invalid() -> None:
    assert is_valid_torrent_hash("too-short") is False
    assert is_valid_torrent_hash("g" * 40) is False
    assert is_valid_torrent_hash("a" * 41) is False


def test_parse_size_empty() -> None:
    assert parse_size("") is None


def test_parse_size_bytes() -> None:
    assert parse_size("100B") == 100


def test_parse_size_kb() -> None:
    assert parse_size("2KB") == 2048


def test_parse_size_mb() -> None:
    assert parse_size("1.5MB") == int(1.5 * 1024**2)


def test_parse_size_gb() -> None:
    assert parse_size("1GB") == 1024**3


def test_parse_size_tb() -> None:
    assert parse_size("2TB") == 2 * 1024**4


def test_parse_size_with_spaces() -> None:
    assert parse_size("  500 MB  ") == 500 * 1024**2


def test_parse_size_invalid() -> None:
    assert parse_size("notasize") is None
    assert parse_size("123XB") is None
