"""Request-shape contract for mutating call sites.

Issue #37: nine call sites posted JSON to endpoints that declare a form or
multipart body, or used the wrong parameter name/location, so the API rejected
the request outright (web download links, referral codes, account deletion,
OAuth registration, magnet torrent lookups, and the vendor mutations).

This module is the checked-in contract: each row names a command, the endpoint
it must reach, the media type it must send, and the parameters or required
fields it must carry. A call site that drifts fails here instead of in
production. The rows below the mutation fixes also pin the endpoints that
already did it right, so the convention cannot rot in one direction only.

The torrent and usenet endpoints that accept an optional file declare
``multipart/form-data``. Without a file the CLI sends the fields as
urlencoded form data, the encodings FastAPI's ``Form`` fields both accept and
the way the sibling call sites have always worked; those rows are therefore
asserted as "form, not JSON" rather than as an exact multipart body.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qsl

import pytest
from typer.testing import CliRunner

from torbox.cli import app

runner = CliRunner()

FORM = "application/x-www-form-urlencoded"
JSON = "application/json"


@dataclass(frozen=True)
class RequestShape:
    """How one command must talk to its endpoint."""

    name: str
    argv: tuple[str, ...]
    method: str
    path: str
    media_type: str | None = None
    params: dict[str, str] = field(default_factory=dict)
    form: dict[str, str] = field(default_factory=dict)
    json_body: dict[str, Any] = field(default_factory=dict)


SHAPES: list[RequestShape] = [
    # --- endpoints the CLI previously posted JSON to (issue #37) ---
    RequestShape(
        "webdl requestdl sends the documented web_id query parameter",
        ("webdl", "requestdl", "7", "1"),
        "GET",
        "/webdl/requestdl",
        params={"token": "dummy", "web_id": "7", "file_id": "1"},
    ),
    RequestShape(
        "user add-referral sends the referral query parameter and no body",
        ("user", "add-referral", "REFERRAL123"),
        "POST",
        "/user/addreferral",
        params={"referral": "REFERRAL123"},
    ),
    RequestShape(
        "user delete sends both fields the schema requires",
        (
            "user",
            "delete",
            "--confirmation-code",
            "1234",
            "--session-token",
            "session-token",
            "--yes",
        ),
        "DELETE",
        "/user/deleteme",
        media_type=JSON,
        json_body={"confirmation_code": 1234, "session_token": "session-token"},
    ),
    RequestShape(
        "integrations oauth register sends token and refresh_token",
        (
            "integrations",
            "oauth",
            "register",
            "googledrive",
            "--token",
            "oauth-token",
            "--refresh-token",
            "oauth-refresh-token",
        ),
        "POST",
        "/integration/oauth/googledrive/register",
        media_type=JSON,
        json_body={"token": "oauth-token", "refresh_token": "oauth-refresh-token"},
    ),
    RequestShape(
        "torrents async-create posts a form body, not JSON",
        ("torrents", "async-create", "--magnet", "magnet:?xt=urn:btih:abc"),
        "POST",
        "/torrents/asynccreatetorrent",
        media_type=FORM,
        form={"magnet": "magnet:?xt=urn:btih:abc"},
    ),
    RequestShape(
        "torrents torrentinfo posts a form body, not JSON",
        ("torrents", "torrentinfo", "--magnet", "magnet:?xt=urn:btih:abc"),
        "POST",
        "/torrents/torrentinfo",
        media_type=FORM,
        form={"magnet": "magnet:?xt=urn:btih:abc"},
    ),
    RequestShape(
        "vendors register posts a form body, not JSON",
        (
            "vendors",
            "register",
            "--vendor-name",
            "Acme",
            "--vendor-url",
            "https://acme.test",
        ),
        "POST",
        "/vendors/register",
        media_type=FORM,
        form={"vendor_name": "Acme", "vendor_url": "https://acme.test"},
    ),
    RequestShape(
        "vendors register-user posts a form body, not JSON",
        ("vendors", "register-user", "--user-email", "user@example.com"),
        "POST",
        "/vendors/registeruser",
        media_type=FORM,
        form={"user_email": "user@example.com"},
    ),
    RequestShape(
        "vendors update-account posts a form body, not JSON",
        ("vendors", "update-account", "--vendor-name", "Acme"),
        "PUT",
        "/vendors/updateaccount",
        media_type=FORM,
        form={"vendor_name": "Acme"},
    ),
    # --- the sibling call sites that already sent form data ---
    RequestShape(
        "torrents create posts the magnet as form data",
        ("torrents", "create", "--magnet", "magnet:?xt=urn:btih:abc"),
        "POST",
        "/torrents/createtorrent",
        media_type=FORM,
        form={"magnet": "magnet:?xt=urn:btih:abc"},
    ),
    RequestShape(
        "usenet create posts the NZB link as form data",
        ("usenet", "create", "https://example.com/file.nzb"),
        "POST",
        "/usenet/createusenetdownload",
        media_type=FORM,
        form={"link": "https://example.com/file.nzb"},
    ),
    RequestShape(
        "webdl create posts the link as form data",
        ("webdl", "create", "https://example.com/file.zip"),
        "POST",
        "/webdl/createwebdownload",
        media_type=FORM,
        form={"link": "https://example.com/file.zip"},
    ),
]

# Commands whose endpoint schema requires a field that the CLI used to send
# only when the caller supplied it. Each must refuse to run without it, rather
# than posting an incomplete body.
REQUIRED_INPUTS = [
    (
        "user delete without --session-token",
        ("user", "delete", "--confirmation-code", "1234", "--yes"),
    ),
    (
        "oauth register without --token",
        ("integrations", "oauth", "register", "googledrive", "--refresh-token", "r"),
    ),
    (
        "oauth register without --refresh-token",
        ("integrations", "oauth", "register", "googledrive", "--token", "t"),
    ),
]


@pytest.fixture
def _stubbed_api(httpx_mock: Any) -> None:
    """Answer any request so the assertion is about the request, not the reply."""
    httpx_mock.add_response(json={"success": True, "data": {}}, is_reusable=True)


@pytest.mark.parametrize("shape", SHAPES, ids=lambda shape: shape.name)
def test_request_shape_matches_contract(
    shape: RequestShape, httpx_mock: Any, _stubbed_api: None
) -> None:
    result = runner.invoke(
        app, list(shape.argv), env={"TORBOX_API_KEY": "dummy"}, input="yes\n"
    )
    assert result.exit_code == 0, result.output

    requests = httpx_mock.get_requests()
    assert len(requests) == 1, f"expected one request, got {len(requests)}"
    request = requests[0]
    assert request.method == shape.method
    assert request.url.path.removeprefix("/v1/api") == shape.path

    if shape.media_type is None:
        assert request.headers.get("content-type") is None, (
            "this endpoint takes its input in the query string, not a body"
        )
        assert parse_qsl(request.content.decode()) == []
    elif shape.media_type == JSON:
        assert request.headers["content-type"] == JSON
    else:
        assert request.headers["content-type"] == FORM, (
            "form endpoints reject a JSON body"
        )

    if shape.media_type == JSON:
        assert json.loads(request.content.decode()) == shape.json_body
    elif shape.form:
        assert dict(parse_qsl(request.content.decode())) == shape.form

    for key, value in shape.params.items():
        assert request.url.params.get(key) == value, (
            f"missing or wrong query parameter {key!r} for {shape.path}"
        )


@pytest.mark.parametrize(
    "name,argv", REQUIRED_INPUTS, ids=[row[0] for row in REQUIRED_INPUTS]
)
def test_required_fields_are_enforced_before_the_request(
    name: str, argv: tuple[str, ...], httpx_mock: Any
) -> None:
    # No response is registered: a request here would be a bug, and the
    # socket guard makes an unmocked request fail loudly.
    result = runner.invoke(app, list(argv), env={"TORBOX_API_KEY": "dummy"})
    assert result.exit_code != 0, f"{name} ran without a required field"
    assert httpx_mock.get_requests() == [], f"{name} sent a request anyway"
