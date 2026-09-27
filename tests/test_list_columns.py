"""Every list command renders a documented column subset (issue #40).

``print_table`` derives its columns from the first item's keys when it is not
given a list. The API returns well over thirty keys per download, so the eleven
call sites that passed nothing rendered columns too narrow to show any content —
the defect already fixed for `torrents list`, `torrents info` and `webdl list`.

Each case below asserts three things: the command passes exactly the documented
subset, every documented column has a header (so a typo in a field name fails
rather than silently rendering an empty column), and a key outside the subset
does not become a column. The payloads carry the polluted key set a raw API item
has, so the old behaviour would fail these assertions.
"""

from __future__ import annotations

from typing import Any

import pytest
from typer.testing import CliRunner

import torbox.commands.integrations as integrations_mod
import torbox.commands.notifications as notifications_mod
import torbox.commands.queued as queued_mod
import torbox.commands.rss as rss_mod
import torbox.commands.usenet as usenet_mod
import torbox.commands.user as user_mod
import torbox.commands.vendors as vendors_mod
import torbox.commands.webdl as webdl_mod
from torbox.cli import app
from torbox.config import DEFAULT_BASE_URL
from torbox.formatters import console

runner = CliRunner()
_ENV = {"TORBOX_API_KEY": "dummy", "NO_COLOR": "1"}

# Keys the API returns that are not part of any documented subset. They must not
# become table columns; `AUTHID` is the value of the `auth_id` junk field, and
# asserting its absence catches a column built from raw keys even if a header
# were truncated.
JUNK = {
    "auth_id": "AUTHID",
    "server": 7,
    "inactive_check": 0,
    "opened": False,
    "file_count": 3,
}
JUNK_VALUE = "AUTHID"

CASES: list[tuple[str, Any, list[str], str, list[str], list[str]]] = [
    (
        "usenet-list",
        usenet_mod,
        ["usenet", "list"],
        f"{DEFAULT_BASE_URL}/usenet/mylist?offset=0&limit=1000",
        [
            "id",
            "name",
            "size",
            "download_state",
            "progress",
            "download_speed",
            "eta",
        ],
        ["id", "name", "size", "download_state", "progress", "download_speed", "eta"],
    ),
    (
        "queued-list",
        queued_mod,
        ["queued", "list"],
        f"{DEFAULT_BASE_URL}/queued/getqueued?offset=0&limit=1000",
        ["id", "name", "hash", "type", "created_at"],
        ["id", "name", "hash", "type", "created_at"],
    ),
    (
        "notifications-list",
        notifications_mod,
        ["notifications", "list"],
        f"{DEFAULT_BASE_URL}/notifications/mynotifications",
        ["id", "title", "message", "created_at"],
        ["id", "title", "message", "created_at"],
    ),
    (
        "rss-list",
        rss_mod,
        ["rss", "list"],
        f"{DEFAULT_BASE_URL}/rss/getfeeds?offset=0&limit=1000",
        ["id", "name", "url", "rss_type", "torrent_seeding", "pass_check"],
        ["id", "name", "url", "rss_type", "torrent_seeding", "pass_check"],
    ),
    (
        "rss-items",
        rss_mod,
        ["rss", "items", "1"],
        f"{DEFAULT_BASE_URL}/rss/getfeeditems?rss_feed_id=1",
        ["id", "title", "size", "pubDate"],
        ["id", "title", "size", "pubDate"],
    ),
    (
        "user-transactions",
        user_mod,
        ["user", "transactions"],
        f"{DEFAULT_BASE_URL}/user/transactions?offset=0&limit=1000",
        ["transaction_id", "type", "amount", "at"],
        ["transaction_id", "type", "amount", "at"],
    ),
    (
        "user-subscriptions",
        user_mod,
        ["user", "subscriptions"],
        f"{DEFAULT_BASE_URL}/user/subscriptions",
        ["plan_name", "plan_code", "status", "gateway", "created_at"],
        ["plan_name", "plan_code", "status", "gateway", "created_at"],
    ),
    (
        "vendors-accounts",
        vendors_mod,
        ["vendors", "accounts"],
        f"{DEFAULT_BASE_URL}/vendors/getaccounts",
        ["user_auth_id", "email", "created_at"],
        ["user_auth_id", "email", "created_at"],
    ),
    (
        "integrations-jobs",
        integrations_mod,
        ["integrations", "jobs", "abc123"],
        f"{DEFAULT_BASE_URL}/integration/jobs/abc123",
        ["id", "type", "integration", "status", "progress", "file_id", "created_at"],
        ["id", "type", "integration", "status", "progress", "file_id", "created_at"],
    ),
    (
        "integrations-list-jobs",
        integrations_mod,
        ["integrations", "list-jobs"],
        f"{DEFAULT_BASE_URL}/integration/jobs",
        ["id", "hash", "type", "integration", "status", "progress", "created_at"],
        ["id", "hash", "type", "integration", "status", "progress", "created_at"],
    ),
    (
        "webdl-hosters",
        webdl_mod,
        ["webdl", "hosters"],
        f"{DEFAULT_BASE_URL}/webdl/hosters",
        [
            "id",
            "name",
            "type",
            "status",
            "url",
            "daily_link_used",
            "daily_link_limit",
        ],
        ["id", "name", "type", "status", "url", "daily_link_used", "daily_link_limit"],
    ),
]


def _payload(columns: list[str]) -> dict[str, Any]:
    """A full-key API item: the documented fields plus the keys that pollute it."""
    item: dict[str, Any] = {column: f"{column}-value" for column in columns}
    item["id"] = 1
    item.update(JUNK)
    return {"success": True, "data": [item]}


# Every key the API documents for a usenet download (GetUsenetListOkResponseData in
# the official SDK). Rendering it through the real formatter is what the issue's
# Definition of Done asks for: named, populated columns on a full-key payload.
USENET_API_KEYS = [
    "active",
    "auth_id",
    "availability",
    "created_at",
    "download_finished",
    "download_present",
    "download_speed",
    "download_state",
    "eta",
    "expires_at",
    "files",
    "hash",
    "id",
    "inactive_check",
    "name",
    "progress",
    "server",
    "size",
    "torrent_file",
    "updated_at",
    "upload_speed",
]


def test_usenet_list_renders_the_documented_columns_for_a_full_api_item(
    monkeypatch: pytest.MonkeyPatch,
    httpx_mock: Any,
) -> None:
    """The real rendering path: no spy, the API's own key set as the payload."""
    # The CLI's console is built at import time, so widen it directly rather than
    # through the environment; at the default 80 columns rich truncates the
    # longer headers regardless of the column list.
    monkeypatch.setattr(console, "width", 200)
    item = {key: f"{key}-value" for key in USENET_API_KEYS}
    item["id"] = 42
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/usenet/mylist?offset=0&limit=1000",
        json={"success": True, "data": [item]},
    )

    result = runner.invoke(app, ["usenet", "list"], env=_ENV)

    assert result.exit_code == 0, result.output
    output = result.output
    for column in (
        "id",
        "name",
        "size",
        "download_state",
        "progress",
        "download_speed",
        "eta",
    ):
        assert column in output
    assert "42" in output and "name-value" in output
    for hidden in ("auth_id", "availability", "upload_speed", "inactive_check"):
        assert f"{hidden}-value" not in output, (
            f"{hidden} is outside the documented subset but was rendered"
        )


@pytest.fixture()
def wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    """Render at a width where no documented header is truncated."""
    monkeypatch.setattr(console, "width", 200)


@pytest.mark.usefixtures("wide_console")
@pytest.mark.parametrize(
    ("module", "argv", "url", "columns", "expected"),
    [case[1:] for case in CASES],
    ids=[case[0] for case in CASES],
)
def test_list_command_renders_only_its_documented_columns(
    monkeypatch: pytest.MonkeyPatch,
    httpx_mock: Any,
    module: Any,
    argv: list[str],
    url: str,
    columns: list[str],
    expected: list[str],
) -> None:
    recorded: dict[str, Any] = {}
    real_print_table = module.print_table

    def spy(
        data: list[dict[str, Any]], title: str = "", columns: list[str] | None = None
    ) -> None:
        recorded["columns"] = columns
        real_print_table(data, title, columns=columns)

    monkeypatch.setattr(module, "print_table", spy)
    httpx_mock.add_response(url=url, json=_payload(expected))

    result = runner.invoke(app, argv, env=_ENV)

    assert result.exit_code == 0, result.output
    assert recorded["columns"] == columns, (
        f"{' '.join(argv)} renders {recorded['columns']} instead of its documented "
        f"subset {columns}; print_table then derives columns from the API keys "
        "(see issue #40)"
    )
    output = result.output
    for column in columns:
        assert column in output, f"{column} has no header; is the field name right?"
    assert JUNK_VALUE not in output, (
        "a key outside the documented subset became a column, so the command is "
        "still rendering raw API keys (see issue #40)"
    )
