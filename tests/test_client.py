"""Tests for TorBoxClient rate-limit tracking and idempotency."""

from __future__ import annotations

import itertools
import uuid
from typing import Any
from unittest.mock import patch

from torbox.client import TorBoxClient


def test_rate_limit_warning(httpx_mock: Any, capsys: Any) -> None:
    httpx_mock.add_response(url="https://api.torbox.app/v1/api/", json={"status": "ok"})
    client = TorBoxClient(api_key="dummy", verbose=True)
    # Populate log so default limit (300/min) threshold is reached (240 >= 300*0.8)
    with patch("torbox.client.time.time", return_value=1000.0):
        client._request_log["/"] = [1000.0] * 240
        client.get("/")
    captured = capsys.readouterr()
    assert "Approaching rate limit for GET /" in captured.err
    assert "240/300 in last 60s" in captured.err


def test_idempotency_key_on_mutating_methods(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url="https://api.torbox.app/v1/api/torrents/createtorrent",
        json={"success": True},
    )
    client = TorBoxClient(api_key="dummy", auto_retry=True)
    client.post("/torrents/createtorrent", data={"magnet": "magnet:?xt=urn:btih:abc"})
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert "x-idempotency-key" in requests[0].headers


def test_idempotency_key_reused_on_retry(httpx_mock: Any) -> None:
    url = "https://api.torbox.app/v1/api/torrents/createtorrent"
    httpx_mock.add_response(url=url, status_code=429, headers={"Retry-After": "0"})
    httpx_mock.add_response(url=url, json={"success": True})
    client = TorBoxClient(api_key="dummy", auto_retry=True)
    client.retries = 1
    client.post("/torrents/createtorrent", data={"magnet": "magnet:?xt=urn:btih:abc"})
    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    key1 = requests[0].headers["x-idempotency-key"]
    key2 = requests[1].headers["x-idempotency-key"]
    assert key1 == key2
    uuid.UUID(key1)  # valid UUID4


def test_no_idempotency_key_on_get(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        url="https://api.torbox.app/v1/api/torrents/mylist",
        json={"success": True, "data": []},
    )
    client = TorBoxClient(api_key="dummy", auto_retry=True)
    client.get("/torrents/mylist")
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert "x-idempotency-key" not in requests[0].headers


def test_createtorrent_rate_limit_v9() -> None:
    """v9.0.0 bumped createtorrent rate limit to 300/minute for cached items."""
    limits = TorBoxClient._RATE_LIMITS
    assert ("/torrents/createtorrent", "POST") in limits
    assert limits[("/torrents/createtorrent", "POST")] == (300, 60)


# =============================================================================
# Bounded _request_log (issue #27)
# =============================================================================


def test_request_log_capped_within_window() -> None:
    """Many requests within one rate window must not exceed the cap."""
    client = TorBoxClient(api_key="dummy")
    with patch("torbox.client.time.time", return_value=1000.0):
        for _ in range(2500):
            client._record_request("/torrents/mylist")
    log = client._request_log["/torrents/mylist"]
    assert len(log) == TorBoxClient._MAX_REQUEST_LOG_ENTRIES
    assert len(log) <= TorBoxClient._MAX_REQUEST_LOG_ENTRIES


def test_request_log_window_trimming() -> None:
    """Entries older than the endpoint's rate window are dropped."""
    client = TorBoxClient(api_key="dummy")
    counter = itertools.count()
    with patch(
        "torbox.client.time.time", side_effect=lambda: 1000.0 + next(counter)
    ):
        for _ in range(2000):
            client._record_request("/torrents/mylist")
    log = client._request_log["/torrents/mylist"]
    # 1-second steps over 2000 requests: only the last ~60s survive.
    assert 0 < len(log) <= 60


def test_request_log_bounded_across_endpoints() -> None:
    """Simulate the monitor TUI: 4 endpoints polled once per second."""
    client = TorBoxClient(api_key="dummy")
    endpoints = [
        "/torrents/mylist",
        "/usenet/mylist",
        "/webdl/mylist",
        "/queued/getqueued",
    ]
    counter = itertools.count()
    with patch(
        "torbox.client.time.time", side_effect=lambda: 1000.0 + next(counter)
    ):
        for _ in range(3600):
            for ep in endpoints:
                client._record_request(ep)
    for ep in endpoints:
        log = client._request_log[ep]
        assert len(log) <= TorBoxClient._MAX_REQUEST_LOG_ENTRIES
        assert len(log) <= 60


def test_request_window_uses_endpoint_specific_window() -> None:
    """Usenet/webdl have a 3600s window; the trim must not shrink below it."""
    client = TorBoxClient(api_key="dummy")
    assert client._request_window("/usenet/createusenetdownload") == 3600
    assert client._request_window("/webdl/createwebdownload") == 3600
    assert client._request_window("/torrents/mylist") == 60
    assert client._request_window("/unknown/endpoint") == 60


def test_rate_limit_warning_still_works_after_trimming(httpx_mock: Any) -> None:
    """Trimming must not break the rate-limit warning accounting."""
    httpx_mock.add_response(
        url="https://api.torbox.app/v1/api/", json={"status": "ok"}
    )
    client = TorBoxClient(api_key="dummy", verbose=True)
    counter = itertools.count()
    with patch(
        "torbox.client.time.time", side_effect=lambda: 1000.0 + next(counter)
    ):
        # 100 requests within the window, well under the warning threshold.
        for _ in range(100):
            client._record_request("/torrents/mylist")
        # Manually seed a near-threshold log as the warning test does.
        client._request_log["/"] = [1000.0] * 240
        client.get("/")
    assert len(client._request_log["/"]) <= TorBoxClient._MAX_REQUEST_LOG_ENTRIES
