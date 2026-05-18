"""Tests for TorBoxClient rate-limit tracking and idempotency."""

from __future__ import annotations

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
