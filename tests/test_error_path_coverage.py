"""Error-path and human-mode coverage for queued, vendors, and integrations.

Targets the thin branches in the three high-risk command modules:
destructive control flows (queued control, vendor removal, integration
cancel/unregister), token-handling OAuth flows, and every raise path.
"""

from __future__ import annotations

import json
from typing import Any

from typer.testing import CliRunner

from tests.conftest import strip_ansi
from torbox.cli import app
from torbox.config import DEFAULT_BASE_URL

runner = CliRunner()
_ENV = {"TORBOX_API_KEY": "dummy"}


# ---------------------------------------------------------------------------
# queued.py — list human mode + control validation/confirmation paths
# ---------------------------------------------------------------------------


def test_queued_list_human_table(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/queued/getqueued?offset=0&limit=1000",
        json={
            "success": True,
            "data": [{"id": 1, "name": "Alpha", "status": "queued"}],
        },
    )
    result = runner.invoke(app, ["queued", "list"], env=_ENV)
    assert result.exit_code == 0
    assert "Alpha" in strip_ansi(result.output)


def test_queued_list_human_empty_panel(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/queued/getqueued?offset=0&limit=1000",
        json={"success": True, "data": None},
    )
    result = runner.invoke(app, ["queued", "list"], env=_ENV)
    assert result.exit_code == 0
    assert "No queued downloads found" in strip_ansi(result.output)


def test_queued_control_confirm_decline_aborts(httpx_mock: Any) -> None:
    """Delete without --yes and declining the prompt aborts with no API call."""
    result = runner.invoke(
        app,
        ["queued", "control", "5", "delete"],
        env=_ENV,
        input="n\n",
    )
    assert result.exit_code == 0
    assert httpx_mock.get_requests() == []


def test_queued_control_confirm_accept_proceeds(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/queued/controlqueued",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        ["queued", "control", "5", "delete"],
        env=_ENV,
        input="y\n",
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert requests[0].method == "POST"
    body = json.loads(requests[0].content)
    assert body["queued_id"] == 5
    assert body["operation"] == "delete"
    assert "completed successfully" in strip_ansi(result.output)


def test_queued_control_success_with_yes(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/queued/controlqueued",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        ["queued", "control", "7", "resume", "--yes"],
        env=_ENV,
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert json.loads(requests[0].content)["operation"] == "resume"


def test_queued_control_json_mode(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/queued/controlqueued",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        ["queued", "control", "7", "pause", "--yes", "--json"],
        env=_ENV,
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["success"] is True


def test_queued_control_invalid_operation_rejected() -> None:
    """Unknown operation must be rejected before any request is sent."""
    result = runner.invoke(
        app,
        ["queued", "control", "5", "bogus", "--yes"],
        env=_ENV,
    )
    assert result.exit_code == 2
    assert "operation must be one of" in strip_ansi(result.output)


# ---------------------------------------------------------------------------
# vendors.py — account/register/refresh/remove/update human and dry-run paths
# ---------------------------------------------------------------------------


def test_vendors_account_human_dict(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/vendors/account",
        json={"success": True, "data": {"vendor_name": "Acme"}},
    )
    result = runner.invoke(app, ["vendors", "account"], env=_ENV)
    assert result.exit_code == 0
    assert "Vendor Account" in strip_ansi(result.output)


def test_vendors_account_human_non_dict(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/vendors/account",
        json={"success": True, "data": None},
    )
    result = runner.invoke(app, ["vendors", "account"], env=_ENV)
    assert result.exit_code == 0
    assert "Vendor account retrieved" in strip_ansi(result.output)


def test_vendors_accounts_human_table(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/vendors/getaccounts",
        json={"success": True, "data": [{"user_auth_id": "ua1"}]},
    )
    result = runner.invoke(app, ["vendors", "accounts"], env=_ENV)
    assert result.exit_code == 0
    assert "ua1" in strip_ansi(result.output)


def test_vendors_accounts_human_empty(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/vendors/getaccounts",
        json={"success": True, "data": None},
    )
    result = runner.invoke(app, ["vendors", "accounts"], env=_ENV)
    assert result.exit_code == 0
    assert "Vendor accounts list retrieved" in strip_ansi(result.output)


def test_vendors_account_info_human_dict(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/vendors/getaccount?user_auth_id=ua1",
        json={"success": True, "data": {"vendor_name": "Acme"}},
    )
    result = runner.invoke(app, ["vendors", "account-info", "ua1"], env=_ENV)
    assert result.exit_code == 0
    assert "Vendor Account ua1" in strip_ansi(result.output)


def test_vendors_account_info_human_non_dict(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/vendors/getaccount?user_auth_id=ua1",
        json={"success": True, "data": None},
    )
    result = runner.invoke(app, ["vendors", "account-info", "ua1"], env=_ENV)
    assert result.exit_code == 0
    assert "Vendor account ua1 retrieved" in strip_ansi(result.output)


def test_vendors_refresh_dry_run() -> None:
    result = runner.invoke(app, ["vendors", "refresh", "--dry-run"], env=_ENV)
    assert result.exit_code == 0
    assert "[dry-run]" in result.output


def test_vendors_refresh_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/vendors/refresh",
        json={"success": True, "data": None},
    )
    result = runner.invoke(app, ["vendors", "refresh"], env=_ENV)
    assert result.exit_code == 0
    assert "Vendor account refreshed" in strip_ansi(result.output)


def test_vendors_register_dry_run_redacts_no_tokens() -> None:
    result = runner.invoke(
        app,
        [
            "vendors",
            "register",
            "--vendor-name",
            "Acme",
            "--vendor-url",
            "https://a.co",
            "--dry-run",
        ],
        env=_ENV,
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "Acme" in result.output


def test_vendors_register_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/vendors/register",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        [
            "vendors",
            "register",
            "--vendor-name",
            "Acme",
            "--vendor-url",
            "https://a.co",
        ],
        env=_ENV,
    )
    assert result.exit_code == 0
    assert "Acme registered" in strip_ansi(result.output)


def test_vendors_register_user_dry_run() -> None:
    result = runner.invoke(
        app,
        ["vendors", "register-user", "--user-email", "u@example.com", "--dry-run"],
        env=_ENV,
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "u@example.com" in result.output


def test_vendors_register_user_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/vendors/registeruser",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        ["vendors", "register-user", "--user-email", "u@example.com"],
        env=_ENV,
    )
    assert result.exit_code == 0
    assert "u@example.com registered" in strip_ansi(result.output)


def test_vendors_remove_user_dry_run() -> None:
    result = runner.invoke(
        app,
        ["vendors", "remove-user", "ua1", "--dry-run"],
        env=_ENV,
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output


def test_vendors_remove_user_confirm_decline_aborts(httpx_mock: Any) -> None:
    result = runner.invoke(
        app,
        ["vendors", "remove-user", "ua1"],
        env=_ENV,
        input="n\n",
    )
    assert result.exit_code == 0
    assert httpx_mock.get_requests() == []


def test_vendors_remove_user_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/vendors/removeuser?user_auth_id=ua1",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        ["vendors", "remove-user", "ua1", "--yes"],
        env=_ENV,
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert requests[0].method == "DELETE"
    assert "ua1 removed" in strip_ansi(result.output)


def test_vendors_update_account_dry_run_with_payload() -> None:
    result = runner.invoke(
        app,
        [
            "vendors",
            "update-account",
            "--vendor-name",
            "Acme",
            "--vendor-url",
            "https://a.co",
            "--dry-run",
        ],
        env=_ENV,
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "Acme" in result.output


def test_vendors_update_account_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/vendors/updateaccount",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        ["vendors", "update-account", "--vendor-name", "Acme"],
        env=_ENV,
    )
    assert result.exit_code == 0
    assert "Vendor account updated" in strip_ansi(result.output)


# ---------------------------------------------------------------------------
# integrations.py — info/jobs/cancel/upload/list-jobs + OAuth lifecycle
# ---------------------------------------------------------------------------


def test_integrations_info_human_dict(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/job/job1",
        json={"success": True, "data": {"id": "job1"}},
    )
    result = runner.invoke(app, ["integrations", "info", "job1"], env=_ENV)
    assert result.exit_code == 0
    assert "Integration Job job1" in strip_ansi(result.output)


def test_integrations_info_human_non_dict(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/job/job1",
        json={"success": True, "data": None},
    )
    result = runner.invoke(app, ["integrations", "info", "job1"], env=_ENV)
    assert result.exit_code == 0
    assert "Integration job job1 retrieved" in strip_ansi(result.output)


def test_integrations_jobs_human_table(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/jobs/abc123",
        json={"success": True, "data": [{"id": "j1", "provider": "dropbox"}]},
    )
    result = runner.invoke(app, ["integrations", "jobs", "abc123"], env=_ENV)
    assert result.exit_code == 0
    assert "j1" in strip_ansi(result.output)


def test_integrations_jobs_human_dict_panel(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/jobs/abc123",
        json={"success": True, "data": {"count": 0}},
    )
    result = runner.invoke(app, ["integrations", "jobs", "abc123"], env=_ENV)
    assert result.exit_code == 0
    assert "Integration Jobs for abc123" in strip_ansi(result.output)


def test_integrations_cancel_confirm_decline_aborts(httpx_mock: Any) -> None:
    result = runner.invoke(
        app,
        ["integrations", "cancel", "job1"],
        env=_ENV,
        input="n\n",
    )
    assert result.exit_code == 0
    assert httpx_mock.get_requests() == []


def test_integrations_cancel_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/job/job1",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        ["integrations", "cancel", "job1", "--yes"],
        env=_ENV,
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert requests[0].method == "DELETE"
    assert "Integration job cancelled" in strip_ansi(result.output)


def test_integrations_upload_invalid_provider_rejected() -> None:
    """Unknown provider must raise a usage error before any request."""
    result = runner.invoke(
        app,
        ["integrations", "upload", "nosuchprovider", "42"],
        env=_ENV,
    )
    assert result.exit_code == 2
    assert "provider must be one of" in strip_ansi(result.output)


def test_integrations_upload_human_with_optional_fields(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/1fichier",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        [
            "integrations",
            "upload",
            "1fichier",
            "42",
            "--zip-link",
            "https://z.co/x.zip",
            "--onefichier-token",
            "of1",
        ],
        env=_ENV,
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    body = json.loads(requests[0].content)
    assert body["file_id"] == 42
    assert body["zip_link"] == "https://z.co/x.zip"
    assert body["onefichier_token"] == "of1"
    assert "Upload queued to 1fichier for file 42" in strip_ansi(result.output)


def test_integrations_upload_json_mode(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/pixeldrain",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        ["integrations", "upload", "pixeldrain", "9", "--json"],
        env=_ENV,
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["success"] is True


def test_integrations_upload_googledrive_token_key(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/googledrive",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        [
            "integrations",
            "upload",
            "googledrive",
            "7",
            "--token",
            "gtok",
        ],
        env=_ENV,
    )
    assert result.exit_code == 0
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["google_token"] == "gtok"


def test_integrations_upload_onedrive_token_key(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/onedrive",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        ["integrations", "upload", "onedrive", "7", "--token", "otok"],
        env=_ENV,
    )
    assert result.exit_code == 0
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["onedrive_token"] == "otok"


def test_integrations_list_jobs_human_table(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/jobs",
        json={"success": True, "data": [{"id": "j1"}]},
    )
    result = runner.invoke(app, ["integrations", "list-jobs"], env=_ENV)
    assert result.exit_code == 0
    assert "j1" in strip_ansi(result.output)


def test_integrations_list_jobs_human_empty(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/jobs",
        json={"success": True, "data": None},
    )
    result = runner.invoke(app, ["integrations", "list-jobs"], env=_ENV)
    assert result.exit_code == 0
    assert "Integration jobs list retrieved" in strip_ansi(result.output)


def test_integrations_oauth_list_human_dict(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/oauth/me",
        json={"success": True, "data": {"googledrive": "linked"}},
    )
    result = runner.invoke(app, ["integrations", "oauth", "list"], env=_ENV)
    assert result.exit_code == 0
    assert "OAuth Integrations" in strip_ansi(result.output)


def test_integrations_oauth_list_human_non_dict(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/oauth/me",
        json={"success": True, "data": None},
    )
    result = runner.invoke(app, ["integrations", "oauth", "list"], env=_ENV)
    assert result.exit_code == 0
    assert "OAuth integrations retrieved" in strip_ansi(result.output)


def test_integrations_oauth_info_human_dict(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/oauth/googledrive",
        json={"success": True, "data": {"status": "linked"}},
    )
    result = runner.invoke(
        app, ["integrations", "oauth", "info", "googledrive"], env=_ENV
    )
    assert result.exit_code == 0
    assert "OAuth googledrive" in strip_ansi(result.output)


def test_integrations_oauth_info_human_non_dict(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/oauth/googledrive",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app, ["integrations", "oauth", "info", "googledrive"], env=_ENV
    )
    assert result.exit_code == 0
    assert "OAuth status for googledrive retrieved" in strip_ansi(result.output)


def test_integrations_oauth_register_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/oauth/googledrive/register",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        [
            "integrations",
            "oauth",
            "register",
            "googledrive",
            "--token",
            "tok1",
            "--refresh-token",
            "ref1",
        ],
        env=_ENV,
    )
    assert result.exit_code == 0
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["token"] == "tok1"
    assert body["refresh_token"] == "ref1"
    assert "googledrive registered" in strip_ansi(result.output)


def test_integrations_oauth_callback_dry_run() -> None:
    result = runner.invoke(
        app,
        ["integrations", "oauth", "callback", "googledrive", "--dry-run"],
        env=_ENV,
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output


def test_integrations_oauth_callback_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/oauth/googledrive/callback",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app, ["integrations", "oauth", "callback", "googledrive"], env=_ENV
    )
    assert result.exit_code == 0
    assert "OAuth callback for googledrive completed" in strip_ansi(result.output)


def test_integrations_oauth_success_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/oauth/googledrive/success",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app, ["integrations", "oauth", "success", "googledrive"], env=_ENV
    )
    assert result.exit_code == 0
    assert "OAuth success page for googledrive retrieved" in strip_ansi(result.output)


def test_integrations_oauth_unregister_dry_run() -> None:
    result = runner.invoke(
        app,
        ["integrations", "oauth", "unregister", "googledrive", "--dry-run"],
        env=_ENV,
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.output


def test_integrations_oauth_unregister_confirm_decline_aborts(
    httpx_mock: Any,
) -> None:
    result = runner.invoke(
        app,
        ["integrations", "oauth", "unregister", "googledrive"],
        env=_ENV,
        input="n\n",
    )
    assert result.exit_code == 0
    assert httpx_mock.get_requests() == []


def test_integrations_oauth_unregister_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/oauth/googledrive/unregister",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        ["integrations", "oauth", "unregister", "googledrive", "--yes"],
        env=_ENV,
    )
    assert result.exit_code == 0
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert requests[0].method == "DELETE"
    assert "googledrive unregistered" in strip_ansi(result.output)


def test_integrations_oauth_discord_linked_roles_human(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url=f"{DEFAULT_BASE_URL}/integration/oauth/discord/linked_roles",
        json={"success": True, "data": None},
    )
    result = runner.invoke(
        app,
        [
            "integrations",
            "oauth",
            "discord-linked-roles",
            "--discord-token",
            "dtok",
        ],
        env=_ENV,
    )
    assert result.exit_code == 0
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["discord_token"] == "dtok"
    assert "Discord linked roles updated" in strip_ansi(result.output)
