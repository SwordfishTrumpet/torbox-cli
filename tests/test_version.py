"""Tests for package version metadata."""

from __future__ import annotations

from torbox import __version__


def test_version_is_string() -> None:
    """__version__ must be a non-empty string."""
    assert isinstance(__version__, str)
    assert len(__version__) > 0
