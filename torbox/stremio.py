"""Stremio addon client for TorBox search endpoints.

WARNING: These endpoints are unofficial and part of TorBox's Stremio
addon, not the official REST API. They may change without notice.
"""

from __future__ import annotations

import re
import sys
import time
from typing import Any

import httpx
from guessit import guessit as _guessit  # type: ignore[import-untyped]

STREMIO_BASE = "https://stremio.torbox.app"
CINEMETA_BASE = "https://v3-cinemeta.strem.io"


class StremioClient:
    """Client for TorBox's Stremio addon endpoints.

    Uses the same API key as the official API but embeds it in the URL
    path rather than an Authorization header.

    Warning: These are unofficial endpoints that may change.
    """

    def __init__(
        self,
        api_key: str | None = None,
        verbose: bool = False,
        auto_retry: bool = False,
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError(
                "API key is required for StremioClient. "
                "Configure TORBOX_API_KEY or use --api-key."
            )
        self.api_key = api_key
        self.verbose = verbose
        self.auto_retry = auto_retry
        self._client = httpx.Client(
            base_url=STREMIO_BASE,
            timeout=timeout,
            headers={"User-Agent": "torbox-cli"},
        )

    @property
    def base_url(self) -> str:
        """https://stremio.torbox.app/{api_key}"""
        return f"{STREMIO_BASE}/{self.api_key}"

    def stream_search(
        self,
        imdb_id: str,
        type: str = "movie",
        season: int | None = None,
        episode: int | None = None,
    ) -> dict[str, Any]:
        sid = imdb_id
        if season is not None and episode is not None:
            sid = f"{imdb_id}:{season}:{episode}"

        path = f"/{self.api_key}/stream/{type}/{sid}.json"

        if self.verbose:
            print(f"[stremio] GET {path}", file=sys.stderr)

        start = time.perf_counter()
        resp = self._request(path)
        elapsed = time.perf_counter() - start

        if self.verbose:
            streams = resp.get("streams", [])
            print(
                f"[stremio] {len(streams)} streams in {elapsed:.2f}s",
                file=sys.stderr,
            )

        return resp

    def library_search(
        self,
        query: str,
        type: str = "movie",
    ) -> dict[str, Any]:
        path = f"/{self.api_key}/catalog/{type}/user-movies/search={query}.json"

        if self.verbose:
            print(f"[stremio] GET {path}", file=sys.stderr)

        start = time.perf_counter()
        resp = self._request(path)
        elapsed = time.perf_counter() - start

        if self.verbose:
            metas = resp.get("metas", [])
            print(
                f"[stremio] {len(metas)} library items in {elapsed:.2f}s",
                file=sys.stderr,
            )

        return resp

    @staticmethod
    def cinemeta_search(
        query: str,
        type: str = "movie",
    ) -> dict[str, Any]:
        url = f"{CINEMETA_BASE}/catalog/{type}/top/search={query}.json"
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return dict(resp.json())

    @staticmethod
    def cinemeta_popular(
        type: str = "movie",
        catalog_id: str = "top",
        skip: int = 0,
    ) -> dict[str, Any]:
        """Fetch popular/top items from Cinemeta (no search query)."""
        url = f"{CINEMETA_BASE}/catalog/{type}/{catalog_id}.json"
        if skip:
            url = f"{url}?skip={skip}"
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return dict(resp.json())

    @staticmethod
    def cinemeta_meta(
        id: str,  # noqa: A002
        type: str = "movie",
    ) -> dict[str, Any]:
        """Fetch full metadata for an IMDB ID from Cinemeta."""
        url = f"{CINEMETA_BASE}/meta/{type}/{id}.json"
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return dict(resp.json())

    def _request(self, path: str, retries: int = 2) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                resp = self._client.get(path)
                resp.raise_for_status()
                return dict(resp.json())
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.NetworkError) as exc:
                last_exc = exc
                if attempt < retries:
                    if self.verbose:
                        print(
                            f"[stremio] {path} -> network error "
                            f"(attempt {attempt + 1}/{retries + 1})",
                            file=sys.stderr,
                        )
                    time.sleep(0.5 * (2**attempt))
                    continue
                raise
            except httpx.HTTPStatusError as exc:
                if (
                    exc.response.status_code == 429
                    and self.auto_retry
                    and attempt < retries
                ):
                    retry_after = int(exc.response.headers.get("Retry-After", "5"))
                    if self.verbose:
                        print(
                            f"[stremio] 429 rate limited, waiting {retry_after}s",
                            file=sys.stderr,
                        )
                    time.sleep(retry_after)
                    continue
                raise

        if last_exc:
            raise last_exc
        raise RuntimeError("Request failed after retries")


def parse_stream_description(desc: str) -> dict[str, str]:
    """Parse a Stremio stream description into structured fields."""
    result: dict[str, str] = {}
    lines = desc.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "|" in line and not line.startswith("Quality:"):
            for part in line.split("|"):
                part = part.strip()
                if ":" in part:
                    key, _, val = part.partition(":")
                    result[key.strip().lower()] = val.strip()
        elif ":" in line:
            key, _, val = line.partition(":")
            result[key.strip().lower()] = val.strip()
    return result


def parse_resolution(name: str) -> str:
    """Extract resolution from a stream name like 'TorBox (Instant) (1080p)'."""
    match = re.search(r"\((\d+p|4k|Unknown)\)", name)
    if match:
        return match.group(1).lower()
    return "unknown"


def is_cached(name: str) -> bool:
    """Check if a stream is cached (Instant) on TorBox."""
    return "(Instant)" in name


def guessit_parse(filename: str) -> dict[str, Any]:
    """Parse a torrent filename with guessit for rich metadata.

    Returns a dict with keys like screen_size, source, video_codec,
    audio_codec, release_group, year, season, episode, etc.
    """
    if not filename:
        return {}
    try:
        result: dict[str, Any] = _guessit(filename)
        return result
    except Exception:
        return {}


def filter_streams(
    streams: list[dict[str, Any]],
    *,
    resolution: str | None = None,
    cached: bool | None = None,
    min_size: int | None = None,
    max_size: int | None = None,
    min_seeders: int | None = None,
    quality: str | None = None,
    source: str | None = None,
    sort: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Filter and sort stream results client-side.

    Uses guessit to parse torrent filenames for rich metadata
    (resolution, source, release group, codecs, year, etc.).
    """
    filtered = []

    for s in streams:
        name = s.get("name", "")
        res = parse_resolution(name)
        c = is_cached(name)
        vsize = s.get("behaviorHints", {}).get("videoSize", 0)
        desc = s.get("description", "")
        parsed = parse_stream_description(desc)
        seeders_str = parsed.get("seeders", "0")
        seeders = int(seeders_str) if seeders_str.isdigit() else 0
        qual = parsed.get("quality", "")
        src = parsed.get("source", "")

        # Guessit: parse the actual torrent filename for richer metadata
        filename = s.get("behaviorHints", {}).get("filename", "") or parsed.get(
            "name", ""
        )
        gi = guessit_parse(filename)

        # Prefer guessit screen_size over manual regex if available
        gi_res = gi.get("screen_size", "")
        if gi_res:
            res = gi_res.lower()

        # Prefer guessit source over description field if available
        gi_src = gi.get("source", "")
        if gi_src:
            src = str(gi_src)

        # Release group from guessit
        group = gi.get("release_group", "")

        # Year from guessit
        year = gi.get("year")

        # Video/audio codecs
        video_codec = gi.get("video_codec", "")
        audio_codec = gi.get("audio_codec", "")

        if resolution and resolution.lower() != res.lower():
            continue
        if cached is not None and c != cached:
            continue
        if min_size is not None and vsize < min_size:
            continue
        if max_size is not None and vsize > max_size:
            continue
        if min_seeders is not None and seeders < min_seeders:
            continue
        if quality and quality.lower() not in qual.lower():
            continue
        if source and source.lower() not in src.lower():
            continue

        gi_serializable = {}
        for k, v in gi.items():
            if hasattr(v, "name"):
                gi_serializable[k] = str(v)
            elif isinstance(v, dict):
                gi_serializable[k] = {
                    sk: str(sv) if hasattr(sv, "name") else sv for sk, sv in v.items()
                }
            else:
                gi_serializable[k] = v

        s["_parsed"] = {
            "resolution": res,
            "cached": c,
            "quality": qual,
            "source": src,
            "seeders": seeders,
            "filename": filename,
            "release_group": group,
            "year": year,
            "video_codec": video_codec,
            "audio_codec": audio_codec,
            "guessit": gi_serializable,
        }
        filtered.append(s)

    if sort == "seeders":
        filtered.sort(key=lambda x: x["_parsed"]["seeders"], reverse=True)
    elif sort == "size":
        filtered.sort(
            key=lambda x: x.get("behaviorHints", {}).get("videoSize", 0),
            reverse=True,
        )
    elif sort == "quality":
        quality_order = {
            "4k": 5,
            "2160p": 5,
            "1080p": 4,
            "720p": 3,
            "480p": 2,
            "unknown": 0,
        }
        filtered.sort(
            key=lambda x: quality_order.get(x["_parsed"]["resolution"].lower(), 0),
            reverse=True,
        )

    return filtered[:limit]
