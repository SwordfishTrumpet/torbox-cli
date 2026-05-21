"""Tests for formatters and JSON/field output."""

from __future__ import annotations

from typing import Any

import pytest
from rich.console import Console

from torbox import formatters
from torbox.formatters import (
    FieldMissingError,
    extract_field,
    print_dict_panel,
    print_error_json,
    print_table,
)


def _capture_console(func: Any, *args: Any, **kwargs: Any) -> str:
    """Run a formatter function against a recording console and return text."""
    old_console = formatters.console
    console = Console(record=True, no_color=True)
    formatters.console = console
    try:
        func(*args, **kwargs)
        return console.export_text()
    finally:
        formatters.console = old_console


def test_print_table_empty(capsys: Any) -> None:
    print_table([], "Test")
    captured = capsys.readouterr()
    assert "No data" in captured.out


def test_extract_field_simple() -> None:
    data = {"success": True, "data": {"name": "foo"}}
    assert extract_field(data, "data.name") == "foo"


def test_extract_field_list() -> None:
    data = {"data": [{"id": 1}, {"id": 2}]}
    assert extract_field(data, "data.0.id") == 1


# --- Snapshot-style tests for human-mode table/panel output stability ---


def test_print_table_snapshot() -> None:
    data = [
        {"name": "Alpha", "size": "1.2 GB"},
        {"name": "Beta", "size": "340 MB"},
    ]
    text = _capture_console(
        print_table, data, title="Downloads", columns=["name", "size"]
    )
    assert "name" in text
    assert "size" in text
    assert "Alpha" in text
    assert "Beta" in text
    assert "1.2 GB" in text
    assert "340 MB" in text


def test_print_dict_panel_snapshot() -> None:
    data = {"id": 42, "status": "completed", "progress": "100%"}
    text = _capture_console(print_dict_panel, data, title="Torrent Info")
    assert "id" in text
    assert "42" in text
    assert "status" in text
    assert "completed" in text
    assert "progress" in text
    assert "100%" in text
    assert "Torrent Info" in text


def test_extract_field_negative_index() -> None:
    data = [1, 2, 3]
    with pytest.raises(FieldMissingError, match="Cannot traverse list"):
        extract_field(data, "-1")


def test_print_error_json(capsys: Any) -> None:
    from torbox.exceptions import TorBoxError

    exc = TorBoxError("test error", exit_code=5)
    print_error_json(exc)
    captured = capsys.readouterr()
    assert "success" in captured.err
    assert "TorBoxError" in captured.err
    assert "test error" in captured.err
    assert "exit_code" in captured.err

    # Test with non-TorBoxError (generic Exception)
    exc2 = Exception("generic error")
    print_error_json(exc2)
    captured2 = capsys.readouterr()
    assert "Exception" in captured2.err
    assert "generic error" in captured2.err
    assert "exit_code" in captured2.err
