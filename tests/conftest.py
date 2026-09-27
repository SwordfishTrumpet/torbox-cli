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
_real_connect_ex = socket.socket.connect_ex
_real_sendto = socket.socket.sendto
# ``sendmsg`` is absent on some platforms (notably Windows).
_real_sendmsg = getattr(socket.socket, "sendmsg", None)
_attempts: list[str] = []

_GUARD_MESSAGE = (
    "Blocked real network connection to {address!r} during tests. "
    "Mock the API with the httpx_mock fixture instead."
)


def _is_loopback(host: object) -> bool:
    return isinstance(host, str) and (
        host.startswith("127.") or host in ("::1", "localhost")
    )


def _guard_address(address: Any) -> None:
    """Fail closed on any non-loopback address (issue #47).

    ``connect`` is not the only way out: ``connect_ex`` returns an error code
    instead of raising, and a datagram socket reaches the network through
    ``sendto``/``sendmsg`` without ever connecting. Every primitive funnels
    through here so the guard cannot be sidestepped by a raw-socket helper.
    """
    host = address[0] if isinstance(address, (tuple, list)) else address
    if _is_loopback(host):
        return
    _attempts.append(str(address))
    raise RuntimeError(_GUARD_MESSAGE.format(address=address))


def _guarded_connect(self: socket.socket, address: Any) -> Any:
    _guard_address(address)
    return _real_connect(self, address)


def _guarded_connect_ex(self: socket.socket, address: Any) -> Any:
    _guard_address(address)
    return _real_connect_ex(self, address)


def _guarded_sendto(self: socket.socket, data: Any, *args: Any) -> Any:
    # sendto(data, address) or sendto(data, flags, address).
    if args:
        _guard_address(args[-1])
    return _real_sendto(self, data, *args)


def _guarded_sendmsg(
    self: socket.socket,
    buffers: Any,
    ancdata: Any = (),
    flags: int = 0,
    address: Any = None,
) -> Any:
    if address is not None:
        _guard_address(address)
    assert _real_sendmsg is not None
    return _real_sendmsg(self, buffers, ancdata, flags, address)


setattr(socket.socket, "connect", _guarded_connect)
setattr(socket.socket, "connect_ex", _guarded_connect_ex)
setattr(socket.socket, "sendto", _guarded_sendto)
if _real_sendmsg is not None:
    setattr(socket.socket, "sendmsg", _guarded_sendmsg)


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
