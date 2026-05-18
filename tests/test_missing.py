"""Tests for general commands and queued (was missing per analysis)."""

from __future__ import annotations

from typing import Any

from typer.testing import CliRunner

from torbox.cli import app

runner = CliRunner()


def test_general_status(httpx_mock: Any) -> None:
    httpx_mock.add_response(url="https://api.torbox.app/v1/api/", json={"status": "ok"})
    result = runner.invoke(app, ["general", "status", "--json"])
    assert result.exit_code == 0
    assert "status" in result.output


def test_general_docs_man() -> None:
    result = runner.invoke(app, ["general", "docs", "--man"])
    assert result.exit_code == 0
    assert ".TH TORBOX" in result.output


def test_queued_list(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url="https://api.torbox.app/v1/api/queued/getqueued?offset=0&limit=1000",
        json={"success": True, "data": []},
    )
    result = runner.invoke(
        app, ["queued", "list", "--json"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code == 0
