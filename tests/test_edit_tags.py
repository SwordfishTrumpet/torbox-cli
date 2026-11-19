"""Tests: usenet/webdl/torrents edit must send tags and alternative_hashes
as arrays of strings (matching the live API schema), not raw comma strings.

Covers issue #25: `usenet edit` and `webdl edit` diverged from the correct
`torrents edit` normalization, sending "a,b" where the API requires
["a", "b"].
"""

from __future__ import annotations

import json
from typing import Any

from typer.testing import CliRunner

from torbox.cli import app
from torbox.config import DEFAULT_BASE_URL

runner = CliRunner()
TEST_KEY = "dummy-test-key"

EDIT_ENDPOINTS = {
    "torrents": "/torrents/edittorrent",
    "usenet": "/usenet/editusenetdownload",
    "webdl": "/webdl/editwebdownload",
}


# Direct parametrized tests per command group.


def _run(group: str, extra: list[str], httpx_mock: Any) -> Any:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}{EDIT_ENDPOINTS[group]}",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        [group, "edit", "10", *extra],
        env={"TORBOX_API_KEY": TEST_KEY},
    )
    assert result.exit_code == 0, result.output
    req = httpx_mock.get_requests()[-1]
    return json.loads(req.content)


def test_torrents_edit_tags_as_array(httpx_mock: Any) -> None:
    body = _run("torrents", ["--tags", "linux,iso,ubuntu"], httpx_mock)
    assert body["tags"] == ["linux", "iso", "ubuntu"]


def test_torrents_edit_alternative_hashes_as_array(httpx_mock: Any) -> None:
    body = _run("torrents", ["--alternative-hashes", "hash1,hash2,hash3"], httpx_mock)
    assert body["alternative_hashes"] == ["hash1", "hash2", "hash3"]


def test_usenet_edit_tags_as_array(httpx_mock: Any) -> None:
    body = _run("usenet", ["--tags", "action,hd,movie"], httpx_mock)
    assert body["tags"] == ["action", "hd", "movie"]


def test_usenet_edit_alternative_hashes_as_array(httpx_mock: Any) -> None:
    body = _run("usenet", ["--alternative-hashes", "h1,h2"], httpx_mock)
    assert body["alternative_hashes"] == ["h1", "h2"]


def test_webdl_edit_tags_as_array(httpx_mock: Any) -> None:
    body = _run("webdl", ["--tags", "series,4k"], httpx_mock)
    assert body["tags"] == ["series", "4k"]


def test_webdl_edit_alternative_hashes_as_array(httpx_mock: Any) -> None:
    body = _run("webdl", ["--alternative-hashes", "aa,bb,cc"], httpx_mock)
    assert body["alternative_hashes"] == ["aa", "bb", "cc"]


def test_edit_trims_whitespace_and_skips_empty_segments(httpx_mock: Any) -> None:
    for group in ("torrents", "usenet", "webdl"):
        body = _run(group, ["--tags", " a ,, b , c "], httpx_mock)
        assert body["tags"] == ["a", "b", "c"], group
        body = _run(group, ["--alternative-hashes", " x ,, y "], httpx_mock)
        assert body["alternative_hashes"] == ["x", "y"], group


def test_edit_id_payload_key(httpx_mock: Any) -> None:
    """Each edit command keeps its own id key; normalization must not disturb it."""
    body = _run("usenet", ["--tags", "a,b"], httpx_mock)
    assert body["usenet_download_id"] == 10
    body = _run("webdl", ["--tags", "a,b"], httpx_mock)
    assert body["webdl_id"] == 10
    body = _run("torrents", ["--tags", "a,b"], httpx_mock)
    assert body["torrent_id"] == 10


def test_edit_omits_fields_not_provided(httpx_mock: Any) -> None:
    """Untouched optional fields must not appear in the payload."""
    body = _run("usenet", [], httpx_mock)
    assert "tags" not in body
    assert "alternative_hashes" not in body
    body = _run("webdl", [], httpx_mock)
    assert "tags" not in body
    assert "alternative_hashes" not in body


# ---------------------------------------------------------------------------
# Explicitly empty values are requests, not omissions (issue #71)
# ---------------------------------------------------------------------------


def test_empty_tags_and_hashes_are_sent_as_empty_arrays(httpx_mock: Any) -> None:
    """`--tags ""` must clear the tags, not silently leave the old ones (#71)."""
    for group in ("torrents", "usenet", "webdl"):
        body = _run(group, ["--tags", "", "--alternative-hashes", ""], httpx_mock)
        assert body["tags"] == [], group
        assert body["alternative_hashes"] == [], group


def test_empty_name_is_sent(httpx_mock: Any) -> None:
    """All three edit commands encode an explicit empty name the same way (#71)."""
    for group in ("torrents", "usenet", "webdl"):
        body = _run(group, ["--name", ""], httpx_mock)
        assert body["name"] == "", group


# ---------------------------------------------------------------------------
# Airlock can be turned off again (issue #72)
# ---------------------------------------------------------------------------


def test_no_airlocked_sends_false(httpx_mock: Any) -> None:
    """A download in permanent storage must be releasable from the CLI (#72)."""
    for group in ("torrents", "usenet", "webdl"):
        body = _run(group, ["--no-airlocked"], httpx_mock)
        assert body["airlocked"] is False, group


def test_airlocked_still_sends_true(httpx_mock: Any) -> None:
    for group in ("torrents", "usenet", "webdl"):
        body = _run(group, ["--airlocked"], httpx_mock)
        assert body["airlocked"] is True, group


def test_airlocked_is_omitted_when_neither_flag_is_given(httpx_mock: Any) -> None:
    for group in ("torrents", "usenet", "webdl"):
        body = _run(group, [], httpx_mock)
        assert "airlocked" not in body, group
