"""Utility helpers: size formatting."""

from __future__ import annotations


def format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size (e.g. 1.2 GB)."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.1f} {units[i]}"
