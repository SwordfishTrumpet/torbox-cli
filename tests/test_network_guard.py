"""Regression tests for the suite's network guard (issue #47).

The guard has to block every primitive a raw-socket helper could use, not just
``socket.connect``: ``connect_ex`` reports the error as a return code, and a
UDP socket sends without connecting at all.

These tests exercise the guard, so they override the suite-wide autouse
fixture in ``conftest.py`` (which would otherwise fail the test for making the
attempt). The non-loopback address is RFC 5737 TEST-NET-1, which is never
routable, so the guard is what stops the call rather than a network timeout.
"""

from __future__ import annotations

import socket
from typing import Any

import pytest

NON_LOOPBACK = "192.0.2.1"


@pytest.fixture(autouse=True)
def _forbid_real_network() -> Any:
    """Override the suite guard for this module: these tests exercise it."""
    yield


def test_connect_blocks_non_loopback() -> None:
    sock = socket.socket()
    try:
        with pytest.raises(RuntimeError, match="Blocked real network connection"):
            sock.connect((NON_LOOPBACK, 443))
    finally:
        sock.close()


def test_connect_ex_blocks_non_loopback() -> None:
    """``connect_ex`` must raise through the guard, not return an error code."""
    sock = socket.socket()
    try:
        with pytest.raises(RuntimeError, match="Blocked real network connection"):
            sock.connect_ex((NON_LOOPBACK, 443))
    finally:
        sock.close()


def test_udp_sendto_blocks_non_loopback() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        with pytest.raises(RuntimeError, match="Blocked real network connection"):
            sock.sendto(b"ping", (NON_LOOPBACK, 53))
    finally:
        sock.close()


def test_loopback_connect_ex_is_still_allowed() -> None:
    """Loopback must reach the real call: a refused port returns non-zero."""
    sock = socket.socket()
    try:
        assert sock.connect_ex(("127.0.0.1", 1)) != 0
    finally:
        sock.close()
