"""HTTP client for TorBox API using httpx with auth and retries."""

from __future__ import annotations

import sys
import time
import uuid
from typing import Any, Literal, overload

import httpx

from torbox.config import load_config
from torbox.exceptions import (
    AuthenticationError,
    ClientError,
    RateLimitError,
    map_error_code,
    map_http_status,
)


class TorBoxClient:
    """Base HTTP client handling auth, retries, and error mapping."""

    _RATE_LIMITS: dict[tuple[str, str], tuple[int, int]] = {
        ("/torrents/createtorrent", "POST"): (60, 3600),
        ("/usenet/createusenetdownload", "POST"): (60, 3600),
        ("/webdl/createwebdownload", "POST"): (60, 3600),
    }
    _DEFAULT_RATE_LIMIT = 300
    _DEFAULT_RATE_WINDOW = 60

    def __init__(
        self,
        api_key: str | None = None,
        config_path: str | None = None,
        profile: str | None = None,
        verbose: bool = False,
        auto_retry: bool = False,
    ) -> None:
        cfg = load_config(
            api_key_override=api_key,
            config_path=config_path,
            profile=profile,
        )
        self.api_key = cfg["api_key"]
        self.base_url = cfg["base_url"]
        self.timeout = cfg["timeout"]
        self.retries = cfg["retries"]
        self.verbose = verbose
        self.auto_retry = auto_retry
        self._request_log: dict[str, list[float]] = {}
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            limits=httpx.Limits(max_connections=20),
        )

    @overload
    def _execute(
        self,
        method: str,
        endpoint: str,
        *,
        auth: bool | str = True,
        return_raw: Literal[False],
        **kwargs: Any,
    ) -> dict[str, Any]: ...

    @overload
    def _execute(
        self,
        method: str,
        endpoint: str,
        *,
        auth: bool | str = True,
        return_raw: Literal[True],
        **kwargs: Any,
    ) -> httpx.Response: ...

    def _execute(
        self,
        method: str,
        endpoint: str,
        *,
        auth: bool | str = True,
        return_raw: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | httpx.Response:
        """Execute an HTTP request with retries, timing, and error mapping.

        Shared helper used by both authenticated (_request) and public
        (public_get) requests to avoid duplicating retry and 429 logic.

        ``auth`` can be ``True`` (required), ``False`` (none), or
        ``"optional"`` (send if available, skip if missing).

        When ``return_raw`` is True, the raw ``httpx.Response`` is returned
        instead of parsing JSON. This is used by ``get_bytes`` and
        ``public_get_bytes``.
        """
        headers = kwargs.pop("headers", {})
        if auth is True:
            if not self.api_key:
                import warnings

                warnings.warn(
                    "No API key configured. Set TORBOX_API_KEY, use --api-key, "
                    "or add it to a .env/config file.",
                    UserWarning,
                    stacklevel=3,
                )
                raise AuthenticationError("No API key configured")
            headers = {**headers, "Authorization": f"Bearer {self.api_key}"}
        elif auth == "optional" and self.api_key:
            headers = {**headers, "Authorization": f"Bearer {self.api_key}"}

        if method in {"POST", "PUT", "DELETE"} and self.auto_retry:
            idempotency_key = str(uuid.uuid4())
            headers = {**headers, "X-Idempotency-Key": idempotency_key}
            if self.verbose:
                print(
                    f"[verbose] Idempotency-Key: {idempotency_key}",
                    file=sys.stderr,
                )

        start = time.perf_counter()
        last_exception: Exception | None = None
        resp: httpx.Response | None = None
        for attempt in range(self.retries + 1):
            if self.verbose:
                self._check_rate_limit_warning(method, endpoint)
            try:
                resp = self.client.request(method, endpoint, headers=headers, **kwargs)
                self._record_request(endpoint)
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.NetworkError) as exc:
                last_exception = exc
                if attempt < self.retries:
                    if self.verbose:
                        print(
                            f"[{method}] {endpoint} -> timeout/network error "
                            f"(attempt {attempt + 1}/{self.retries + 1})",
                            file=sys.stderr,
                        )
                    time.sleep(0.5 * (2**attempt))  # exponential backoff
                    continue
                break

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After", "")
                if self.auto_retry and attempt < self.retries:
                    wait = (
                        int(retry_after)
                        if retry_after and retry_after.isdigit()
                        else 2**attempt
                    )
                    if self.verbose:
                        print(
                            f"[{method}] {endpoint} -> 429, auto-retrying in {wait}s "
                            f"(attempt {attempt + 1}/{self.retries + 1})",
                            file=sys.stderr,
                        )
                    time.sleep(wait)
                    continue
                msg = (
                    f"Rate limited. Retry after {retry_after}s."
                    if retry_after
                    else "Rate limited. Please retry after a while."
                )
                raise RateLimitError(msg)

            break  # success or non-429 non-timeout status

        duration = (time.perf_counter() - start) * 1000
        if self.verbose:
            if resp is not None:
                print(
                    f"[{method}] {endpoint} -> {resp.status_code} ({duration:.1f}ms)",
                    file=sys.stderr,
                )
            elif last_exception is not None:
                print(
                    f"[{method}] {endpoint} -> {type(last_exception).__name__} "
                    f"({duration:.1f}ms)",
                    file=sys.stderr,
                )

        if resp is None and last_exception is not None:
            raise ClientError(
                f"Request failed after {self.retries + 1} attempts: {last_exception}"
            )

        assert resp is not None

        if not resp.is_success:
            raise map_http_status(resp.status_code, resp.text)
        if return_raw:
            return resp
        result: dict[str, Any] = resp.json()
        return result

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Perform authenticated request and map API-level errors."""
        data = self._execute(method, endpoint, auth=True, return_raw=False, **kwargs)
        if not data.get("success", True):
            raise map_error_code(
                data.get("error", "UNKNOWN_ERROR"), data.get("detail", "")
            )
        return data

    def get(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        return self._request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        return self._request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        return self._request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        return self._request("DELETE", endpoint, **kwargs)

    def public_get(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Public GET without auth (for general endpoints)."""
        return self._execute("GET", endpoint, auth=False, return_raw=False, **kwargs)

    def optional_get(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """GET with optional auth: sends Bearer if key is available.

        Use for endpoints where auth is optional (e.g. /webdl/hosters).
        """
        return self._execute(
            "GET", endpoint, auth="optional", return_raw=False, **kwargs
        )

    def get_bytes(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """Perform authenticated GET and return raw response object.

        Useful for endpoints that return non-JSON data (e.g. PDFs, .torrent
        files). Delegates to ``_execute`` so retries, 429 handling, and
        verbose logging are preserved without duplication.
        """
        raw = self._execute("GET", endpoint, auth=True, return_raw=True, **kwargs)
        assert isinstance(raw, httpx.Response)
        return raw

    def post_bytes(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """Perform authenticated POST and return raw response object.

        Use for endpoints that return non-JSON data on POST (e.g.
        ``/torrents/magnettofile`` which returns raw .torrent bytes).
        """
        raw = self._execute("POST", endpoint, auth=True, return_raw=True, **kwargs)
        assert isinstance(raw, httpx.Response)
        return raw

    def public_get_bytes(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """Public GET without auth, returning raw response object.

        Use for endpoints that return non-JSON data and require no
        authentication (e.g. ``/changelogs/rss``).
        """
        raw = self._execute("GET", endpoint, auth=False, return_raw=True, **kwargs)
        assert isinstance(raw, httpx.Response)
        return raw

    def _check_rate_limit_warning(self, method: str, endpoint: str) -> None:
        limit, window = self._RATE_LIMITS.get(
            (endpoint, method), (self._DEFAULT_RATE_LIMIT, self._DEFAULT_RATE_WINDOW)
        )
        log = self._request_log.get(endpoint, [])
        now = time.time()
        # Clean up old timestamps older than the window
        recent = [t for t in log if now - t < window]
        self._request_log[endpoint] = recent
        count = len(recent)
        if count >= limit * 0.8:
            print(
                f"[verbose] Approaching rate limit for {method} {endpoint} "
                f"({count}/{limit} in last {window}s)",
                file=sys.stderr,
            )

    def _record_request(self, endpoint: str) -> None:
        now = time.time()
        self._request_log.setdefault(endpoint, []).append(now)

    def close(self) -> None:
        self.client.close()
