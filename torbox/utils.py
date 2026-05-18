"""Utility helpers: size formatting, date parsing, hash validation."""

from __future__ import annotations

import re
from datetime import datetime


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


def parse_date(date_str: str) -> datetime | None:
    """Parse common date formats from API."""
    formats = ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def is_valid_torrent_hash(hash_str: str) -> bool:
    """Validate SHA1 or info-hash (40 hex chars)."""
    return bool(re.fullmatch(r"[a-fA-F0-9]{40}", hash_str))
