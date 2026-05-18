"""Tests for general commands and queued (was missing per analysis)."""

from __future__ import annotations

from typer.testing import CliRunner

from torbox.cli import app

runner = CliRunner()


def test_general_status(httpx_mock):
    httpx_mock.add_response(url="https://api.torbox.app/v1/", json={"status": "ok"})
    result = runner.invoke(app, ["general", "status", "--json"])
    assert result.exit_code == 0
    assert "status" in result.output


def test_general_docs_man():
    result = runner.invoke(app, ["general", "docs", "--man"])
    assert result.exit_code == 0
    assert ".TH TORBOX" in result.output


def test_queued_list(httpx_mock):
    httpx_mock.add_response(
        url="https://api.torbox.app/v1/queued/getqueued",
        json={"success": True, "data": []},
    )
    result = runner.invoke(
        app, ["queued", "list", "--json"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code == 0
