"""A missing ``--field`` must not turn a committed write into a failure (#64).

The envelope was printed after the request went out, and a ``--field`` path the
response does not carry raised ``exit 1``. Automation that retries on nonzero
then wrote twice. A write is committed by the time the envelope is rendered, so
the miss is reported on stderr and the exit status stays a success; a read that
asked for a field it did not get is still a usage error.
"""

from __future__ import annotations

from typing import Any

from typer.testing import CliRunner

from torbox.cli import app

runner = CliRunner()
MISSING = "data.__no_such_field__"


def test_create_with_missing_field_exits_zero_after_one_write(
    httpx_mock: Any,
) -> None:
    httpx_mock.add_response(json={"success": True, "data": {"id": 1}})
    result = runner.invoke(
        app,
        [
            "--json",
            "--field",
            MISSING,
            "torrents",
            "create",
            "--magnet",
            "magnet:?xt=urn:btih:abc",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0, result.output
    assert len(httpx_mock.get_requests()) == 1
    assert "null" in result.output


def test_get_that_mutates_also_exits_zero(httpx_mock: Any) -> None:
    """``stream create`` changes state over GET, so the method alone cannot decide."""
    httpx_mock.add_response(json={"success": True, "data": {"token": "tok"}})
    result = runner.invoke(
        app,
        ["--json", "--field", MISSING, "stream", "create", "1", "torrent"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0, result.output
    assert len(httpx_mock.get_requests()) == 1


def test_read_with_missing_field_still_exits_one(httpx_mock: Any) -> None:
    httpx_mock.add_response(json={"success": True, "data": []})
    result = runner.invoke(
        app,
        ["--json", "--field", MISSING, "torrents", "list"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 1
    assert len(httpx_mock.get_requests()) == 1


def test_a_found_field_still_prints_it(httpx_mock: Any) -> None:
    httpx_mock.add_response(json={"success": True, "data": {"id": 7}})
    result = runner.invoke(
        app,
        [
            "--json",
            "--field",
            "data.data.id",
            "torrents",
            "create",
            "--magnet",
            "magnet:?xt=urn:btih:abc",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "7"
