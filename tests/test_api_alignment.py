"""Tests for API alignment fixes (base URL, parameters, field names, endpoints)."""

from __future__ import annotations

import json
from typing import Any

from typer.testing import CliRunner

from torbox.cli import app
from torbox.config import DEFAULT_BASE_URL
from torbox.exceptions import ServerError, map_error_code

runner = CliRunner()


# --- Base URL ---


def test_default_base_url_includes_api_suffix() -> None:
    assert DEFAULT_BASE_URL.endswith("/api")


# --- Torrents create parameters ---


def test_torrents_create_with_seed_and_name(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/createtorrent",
        json={"success": True, "data": {"id": 1}},
    )
    result = runner.invoke(
        app,
        [
            "torrents",
            "create",
            "--magnet",
            "magnet:?xt=urn:btih:abc",
            "--seed",
            "2",
            "--name",
            "My Torrent",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    content_type = requests[0].headers.get("content-type", "")
    assert content_type.startswith("application/x-www-form-urlencoded")
    body = requests[0].content.decode()
    assert "seed=2" in body
    assert "name=My+Torrent" in body


# --- Torrents control --all ---


def test_torrents_control_all_flag(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/controltorrent",
        json={"success": True},
    )
    result = runner.invoke(
        app,
        ["torrents", "control", "--operation", "pause", "--all"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    body = json.loads(requests[0].content)
    assert body["all"] == 1
    assert body["operation"] == "pause"
    assert "torrent_id" not in body


def test_torrents_control_all_and_id_exclusive() -> None:
    result = runner.invoke(
        app,
        ["torrents", "control", "42", "--operation", "delete", "--all"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_torrents_control_no_id_no_all() -> None:
    result = runner.invoke(
        app,
        ["torrents", "control", "--operation", "delete"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code != 0
    assert "Either provide an ID or use --all" in result.output


# --- Torrents requestdl parameters ---


def test_torrents_requestdl_with_flags(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/torrents/requestdl?torrent_id=1&file_id=2&token=dummy&zip_link=1&user_ip=1.2.3.4&redirect=1&append_name=1",
        json={"success": True, "data": {"link": "https://example.com"}},
    )
    result = runner.invoke(
        app,
        [
            "torrents",
            "requestdl",
            "1",
            "2",
            "--zip-link",
            "--user-ip",
            "1.2.3.4",
            "--redirect",
            "--append-name",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0


# --- Usenet create parameters ---


def test_usenet_create_with_name_and_password(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/usenet/createusenetdownload",
        json={"success": True, "data": {"id": 1}},
    )
    result = runner.invoke(
        app,
        [
            "usenet",
            "create",
            "https://example.com/file.nzb",
            "--name",
            "My NZB",
            "--password",
            "secret",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    content_type = requests[0].headers.get("content-type", "")
    assert content_type.startswith("application/x-www-form-urlencoded")
    body = requests[0].content.decode()
    assert "name=My+NZB" in body
    assert "password=secret" in body


# --- Usenet control --all ---


def test_usenet_control_all_flag(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/usenet/controlusenetdownload",
        json={"success": True},
    )
    result = runner.invoke(
        app,
        ["usenet", "control", "--operation", "delete", "--all", "--yes"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    body = json.loads(requests[0].content)
    assert body["all"] == 1
    assert "usenet_id" not in body


# --- Usenet requestdl parameters ---


def test_usenet_requestdl_with_flags(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/usenet/requestdl?usenet_id=1&file_id=2&token=dummy&zip_link=1",
        json={"success": True, "data": {"link": "https://example.com"}},
    )
    result = runner.invoke(
        app,
        ["usenet", "requestdl", "1", "2", "--zip-link"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0


# --- Webdl create formdata and parameters ---


def test_webdl_create_formdata_with_flags(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/webdl/createwebdownload",
        json={"success": True, "data": {"id": 1}},
    )
    result = runner.invoke(
        app,
        [
            "webdl",
            "create",
            "https://example.com/file.zip",
            "--password",
            "pass",
            "--name",
            "My File",
            "--as-queued",
            "--add-only-if-cached",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    assert (
        requests[0]
        .headers.get("content-type", "")
        .startswith("application/x-www-form-urlencoded")
    )
    body = requests[0].content.decode()
    assert "password=pass" in body
    assert "name=My+File" in body
    assert "as_queued=1" in body
    assert "add_only_if_cached=1" in body


# --- Webdl control webdl_id and --all ---


def test_webdl_control_uses_webdl_id(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/webdl/controlwebdownload",
        json={"success": True},
    )
    result = runner.invoke(
        app,
        ["webdl", "control", "10", "--operation", "delete", "--yes"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    body = json.loads(requests[0].content)
    assert body["webdl_id"] == 10
    assert "web_id" not in body


def test_webdl_control_all_flag(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/webdl/controlwebdownload",
        json={"success": True},
    )
    result = runner.invoke(
        app,
        ["webdl", "control", "--operation", "delete", "--all", "--yes"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    body = json.loads(requests[0].content)
    assert body["all"] == 1
    assert "webdl_id" not in body


# --- Webdl edit parameters ---


def test_webdl_edit_with_payload(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/webdl/editwebdownload",
        json={"success": True},
    )
    result = runner.invoke(
        app,
        [
            "webdl",
            "edit",
            "5",
            "--name",
            "Updated",
            "--tags",
            "tag1,tag2",
            "--alternative-hashes",
            "abc,def",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    body = json.loads(requests[0].content)
    assert body["webdl_id"] == 5
    assert body["name"] == "Updated"
    assert body["tags"] == "tag1,tag2"
    assert body["alternative_hashes"] == "abc,def"


# --- User auth-device-start --app ---


def test_user_auth_device_start_with_app(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/auth/device/start?app=MyApp",
        json={"success": True, "data": {"code": "123456"}},
    )
    result = runner.invoke(
        app,
        ["user", "auth-device-start", "--app", "MyApp", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "123456" in result.output


# --- User me --settings ---


def test_user_me_settings_flag(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/me?settings=true",
        json={"success": True, "data": {"email": "a@b.com"}},
    )
    result = runner.invoke(
        app,
        ["user", "me", "--settings", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    assert "a@b.com" in result.output


# --- User settings PUT ---


def test_user_settings_put_with_json(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/settings/editsettings",
        json={"success": True},
    )
    result = runner.invoke(
        app,
        ["user", "settings", "--body", '{"theme":"dark"}'],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    body = json.loads(requests[0].content)
    assert body["theme"] == "dark"


# --- User searchengines --id ---


def test_user_searchengines_with_id(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/settings/searchengines?id=3",
        json={"success": True, "data": {"id": 3}},
    )
    result = runner.invoke(
        app,
        ["user", "searchengines", "--id", "3", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0


# --- User transaction-pdf transaction_id ---


def test_user_transaction_pdf_uses_transaction_id(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/user/transaction/pdf?transaction_id=99",
        json={"success": True, "data": {"url": "https://example.com/pdf"}},
    )
    result = runner.invoke(
        app,
        ["user", "transaction-pdf", "99", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0


# --- RSS list --id ---


def test_rss_list_with_id(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/rss/getfeeds?offset=0&limit=1000&id=7",
        json={"success": True, "data": {"id": 7}},
    )
    result = runner.invoke(
        app,
        ["rss", "list", "--id", "7", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0


# --- RSS items rss_feed_id ---


def test_rss_items_uses_rss_feed_id(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/rss/getfeeditems?rss_feed_id=2",
        json={"success": True, "data": []},
    )
    result = runner.invoke(
        app,
        ["rss", "items", "2", "--json"],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0


# --- Stream create parameters ---


def test_stream_create_with_flags(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/stream/createstream?id=1&type=torrent&file_id=10&chosen_subtitle_index=0&chosen_audio_index=1&chosen_resolution_index=2",
        json={"success": True, "data": {"token": "abc"}},
    )
    result = runner.invoke(
        app,
        [
            "stream",
            "create",
            "1",
            "torrent",
            "--file-id",
            "10",
            "--chosen-subtitle-index",
            "0",
            "--chosen-audio-index",
            "1",
            "--chosen-resolution-index",
            "2",
            "--json",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0


# --- Stream data parameters ---


def test_stream_data_with_flags(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/stream/getstreamdata?presigned_token=xyz&token=dummy&chosen_subtitle_index=0&chosen_audio_index=1&chosen_resolution_index=2",
        json={"success": True, "data": {"url": "https://example.com"}},
    )
    result = runner.invoke(
        app,
        [
            "stream",
            "data",
            "xyz",
            "--chosen-subtitle-index",
            "0",
            "--chosen-audio-index",
            "1",
            "--chosen-resolution-index",
            "2",
            "--json",
        ],
        env={"TORBOX_API_KEY": "dummy"},
    )
    assert result.exit_code == 0


# --- General changelogs --format rss ---


def test_general_changelogs_rss_format(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/changelogs/rss",
        text="<rss><channel></channel></rss>",
    )
    result = runner.invoke(app, ["general", "changelogs", "--format", "rss", "--json"])
    assert result.exit_code == 0
    assert "<rss>" in result.output


# --- UNSUPPORTED_SITE error code ---


def test_unsupported_site_error_code() -> None:
    exc = map_error_code("UNSUPPORTED_SITE", "Site not supported")
    assert isinstance(exc, ServerError)
    assert exc.exit_code == 3
