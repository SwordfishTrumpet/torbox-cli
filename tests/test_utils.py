"""Tests for utility helpers."""

from __future__ import annotations

import inspect

import torbox.utils as utils
from torbox.utils import format_size


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


def test_utils_exports_only_helpers_with_a_call_site() -> None:
    """Every public helper must be used by application code (issue #46).

    ``format_size`` is imported by ``torbox/commands/monitor.py``; the module
    must not grow another public helper until a command actually imports it.
    """
    defined = [
        name
        for name, obj in vars(utils).items()
        if inspect.isfunction(obj) and obj.__module__ == utils.__name__
    ]
    assert defined == ["format_size"]
