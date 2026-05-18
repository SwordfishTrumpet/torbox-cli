"""TorBox CLI package."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    _v = version("torbox-cli")
    __version__ = _v if _v else "0.0.0+unknown"
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+unknown"
