"""HTTP client for TorBox API using httpx with auth and retries."""

from __future__ import annotations

from typing import Any

import httpx

from torbox.config import load_config
from torbox.exceptions import AuthenticationError, map_error_code


class TorBoxClient:
    """Base HTTP client handling auth, retries, and error mapping."""

    def __init__(self, api_key: str | None = None, config_path: Any = None) -> None:
        cfg = load_config(api_key_override=api_key)
        self.api_key = cfg["api_key"]
        self.base_url = cfg["base_url"]
        self.timeout = cfg["timeout"]
        self.retries = cfg["retries"]
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            limits=httpx.Limits(max_connections=20),
        )

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        """Perform request with auth header and basic retry on 429."""
        if not self.api_key:
            raise AuthenticationError("No API key configured")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        for attempt in range(self.retries + 1):
            resp = self.client.request(method, endpoint, headers=headers, **kwargs)
            if resp.status_code == 429 and attempt < self.retries:
                continue  # simple retry
            break
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success", True):
            raise map_error_code(
                data.get("error", "UNKNOWN_ERROR"), data.get("detail", "")
            )
        return data

    def get(self, endpoint: str, **kwargs: Any) -> Any:
        return self._request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs: Any) -> Any:
        return self._request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs: Any) -> Any:
        return self._request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs: Any) -> Any:
        return self._request("DELETE", endpoint, **kwargs)

    def public_get(self, endpoint: str, **kwargs: Any) -> Any:
        """Public GET without auth (for general endpoints)."""
        for attempt in range(self.retries + 1):
            resp = self.client.request("GET", endpoint, **kwargs)
            if resp.status_code == 429 and attempt < self.retries:
                continue
            break
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self.client.close()
