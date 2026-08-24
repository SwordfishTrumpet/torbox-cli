"""Test suite guards.

Blocks real (non-loopback) network connections during the test run so that
no test can silently depend on the live TorBox API. Any test that attempts a
real connection is failed explicitly, even if the command under test swallows
the resulting error. This keeps the suite deterministic and offline.
"""

from __future__ import annotations

import re
import socket
from typing import Any

import pytest

# ANSI SGR escape sequences: CI runners (GITHUB_ACTIONS=true) make rich/click
# render colored output, which interleaves escape codes into option names
# (e.g. "--all" becomes "-" + "-all" styled spans), breaking plain-text
# substring assertions. Strip them before asserting on CLI output.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI color/format escape sequences from CLI output."""
    return _ANSI_RE.sub("", text)

_real_connect = socket.socket.connect
_attempts: list[str] = []


def _is_loopback(host: object) -> bool:
    return isinstance(host, str) and (
        host.startswith("127.") or host in ("::1", "localhost")
    )


def _guarded_connect(self: socket.socket, address: Any) -> Any:
    host = address[0] if isinstance(address, (tuple, list)) else address
    if _is_loopback(host):
        return _real_connect(self, address)
    _attempts.append(str(address))
    raise RuntimeError(
        f"Blocked real network connection to {address!r} during tests. "
        "Mock the API with the httpx_mock fixture instead."
    )


setattr(socket.socket, "connect", _guarded_connect)


@pytest.fixture(autouse=True)
def _forbid_real_network() -> Any:
    """Fail any test that attempts a real network connection."""
    start = len(_attempts)
    yield
    made = _attempts[start:]
    if made:
        pytest.fail(
            "Test attempted real network connection(s): "
            f"{made}. Mock the API with httpx_mock."
        )
