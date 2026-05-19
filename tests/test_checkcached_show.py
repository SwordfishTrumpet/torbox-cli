"""Tests for checkcached show and related Stremio helpers."""

from __future__ import annotations

from typing import Any

import pytest
from typer.testing import CliRunner

from torbox.cli import app
from torbox.commands.torrents import _aggregate_episode, _parse_episodes_filter
from torbox.config import DEFAULT_BASE_URL
from torbox.stremio import (
    StremioClient,
    discover_episodes,
    stream_search_bulk,
)

runner = CliRunner()

CINEMETA_BASE = "https://v3-cinemeta.strem.io"
STREMIO_BASE = "https://stremio.torbox.app"


def _make_stream(name: str, desc: str, vsize: int) -> dict[str, Any]:
    return {
        "name": name,
        "description": desc,
        "behaviorHints": {"videoSize": vsize},
    }


MOCK_DESC = (
    "Quality: BLURAY\n"
    "Name: The.Matrix.1999.1080p.BrRip.x264.YIFY.mp4\n"
    "Size: 2GB | Source: torrentscsv\n"
    "Language: UNKNOWN\n"
    "Type: Torrent | Seeders: 704"
)


class TestDiscoverEpisodes:
    def test_discover_all_episodes(self, httpx_mock: Any) -> None:
        mock_response = {
            "meta": {
                "id": "tt0944947",
                "name": "Game of Thrones",
                "videos": [
                    {
                        "id": "tt0944947:1:1",
                        "season": 1,
                        "episode": 1,
                        "title": "Winter Is Coming",
                        "released": "2011-04-17",
                    },
                    {
                        "id": "tt0944947:1:2",
                        "season": 1,
                        "episode": 2,
                        "title": "The Kingsroad",
                        "released": "2011-04-24",
                    },
                    {
                        "id": "tt0944947:2:1",
                        "season": 2,
                        "episode": 1,
                        "title": "The North Remembers",
                        "released": "2012-04-01",
                    },
                ],
            }
        }
        httpx_mock.add_response(
            url=f"{CINEMETA_BASE}/meta/series/tt0944947.json",
            json=mock_response,
        )
        result = discover_episodes("tt0944947")
        assert len(result) == 3
        assert result[0]["season"] == 1
        assert result[0]["episode"] == 1
        assert result[0]["title"] == "Winter Is Coming"
        assert result[2]["season"] == 2
        assert result[2]["episode"] == 1

    def test_discover_season_filter(self, httpx_mock: Any) -> None:
        mock_response = {
            "meta": {
                "videos": [
                    {"id": "tt0944947:1:1", "season": 1, "episode": 1, "title": "S1E1"},
                    {"id": "tt0944947:2:1", "season": 2, "episode": 1, "title": "S2E1"},
                ],
            }
        }
        httpx_mock.add_response(
            url=f"{CINEMETA_BASE}/meta/series/tt0944947.json",
            json=mock_response,
        )
        result = discover_episodes("tt0944947", season=2)
        assert len(result) == 1
        assert result[0]["season"] == 2

    def test_discover_no_videos(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{CINEMETA_BASE}/meta/series/tt0944947.json",
            json={"meta": {}},
        )
        result = discover_episodes("tt0944947")
        assert result == []


class TestStreamSearchBulk:
    def test_bulk_parallel(self, httpx_mock: Any) -> None:
        api_key = "test-key"
        imdb_id = "tt0944947"

        httpx_mock.add_response(
            url=f"{STREMIO_BASE}/{api_key}/stream/series/{imdb_id}:1:1.json",
            json={"streams": [{"name": "TorBox (Instant) (1080p)"}]},
        )
        httpx_mock.add_response(
            url=f"{STREMIO_BASE}/{api_key}/stream/series/{imdb_id}:1:2.json",
            json={"streams": [{"name": "TorBox (720p)"}]},
        )

        client = StremioClient(api_key=api_key)
        result = stream_search_bulk(client, imdb_id, [(1, 1), (1, 2)], max_workers=2)
        assert len(result) == 2
        assert len(result[(1, 1)]) == 1
        assert len(result[(1, 2)]) == 1
        assert result[(1, 1)][0]["name"] == "TorBox (Instant) (1080p)"

    def test_bulk_empty_response(self, httpx_mock: Any) -> None:
        api_key = "test-key"
        imdb_id = "tt0944947"
        httpx_mock.add_response(
            url=f"{STREMIO_BASE}/{api_key}/stream/series/{imdb_id}:1:1.json",
            json={"streams": []},
        )
        client = StremioClient(api_key=api_key)
        result = stream_search_bulk(client, imdb_id, [(1, 1)])
        assert result[(1, 1)] == []


class TestParseEpisodesFilter:
    def test_valid(self) -> None:
        assert _parse_episodes_filter("1,2,3") == [1, 2, 3]
        assert _parse_episodes_filter("10") == [10]

    def test_none(self) -> None:
        assert _parse_episodes_filter(None) is None

    def test_invalid(self) -> None:
        with pytest.raises(Exception):
            _parse_episodes_filter("a,b")


class TestAggregateEpisode:
    def test_empty(self) -> None:
        agg = _aggregate_episode([])
        assert agg["cached"] is False
        assert agg["streams_count"] == 0

    def test_cached(self) -> None:
        streams = [
            _make_stream("TorBox (Instant) (1080p)", MOCK_DESC, 2_000_000_000),
            _make_stream("TorBox (720p)", MOCK_DESC, 1_000_000_000),
        ]
        from torbox.stremio import filter_streams

        filtered = filter_streams(streams)
        agg = _aggregate_episode(filtered)
        assert agg["cached"] is True
        assert agg["streams_count"] == 2
        assert agg["cached_streams_count"] == 1
        assert agg["best_resolution"] == "1080p"
        assert agg["best_seeders"] == 704

    def test_not_cached(self) -> None:
        streams = [
            _make_stream("TorBox (1080p)", MOCK_DESC, 2_000_000_000),
        ]
        from torbox.stremio import filter_streams

        filtered = filter_streams(streams)
        agg = _aggregate_episode(filtered)
        assert agg["cached"] is False
        assert agg["cached_streams_count"] == 0
        assert agg["best_resolution"] == "1080p"


class TestCheckcachedShowCommand:
    def test_show_basic(self, httpx_mock: Any) -> None:
        api_key = "test-key"
        imdb_id = "tt0944947"

        # Cinemeta meta
        httpx_mock.add_response(
            url=f"{CINEMETA_BASE}/meta/series/{imdb_id}.json",
            json={
                "meta": {
                    "videos": [
                        {
                            "id": f"{imdb_id}:1:1",
                            "season": 1,
                            "episode": 1,
                            "title": "Winter Is Coming",
                        },
                        {
                            "id": f"{imdb_id}:1:2",
                            "season": 1,
                            "episode": 2,
                            "title": "The Kingsroad",
                        },
                    ],
                }
            },
        )

        # Stremio streams per episode
        httpx_mock.add_response(
            url=f"{STREMIO_BASE}/{api_key}/stream/series/{imdb_id}:1:1.json",
            json={
                "streams": [
                    {
                        "name": "TorBox (Instant) (1080p)",
                        "description": MOCK_DESC,
                        "behaviorHints": {"videoSize": 2_000_000_000},
                    }
                ]
            },
        )
        httpx_mock.add_response(
            url=f"{STREMIO_BASE}/{api_key}/stream/series/{imdb_id}:1:2.json",
            json={
                "streams": [
                    {
                        "name": "TorBox (720p)",
                        "description": MOCK_DESC,
                        "behaviorHints": {"videoSize": 1_000_000_000},
                    }
                ]
            },
        )

        result = runner.invoke(
            app,
            ["torrents", "checkcached", "show", imdb_id, "--season", "1", "--json"],
            env={"TORBOX_API_KEY": api_key},
        )
        assert result.exit_code == 0
        assert "Winter Is Coming" in result.output
        assert "The Kingsroad" in result.output
        assert "true" in result.output or "True" in result.output

    def test_show_cached_filter(self, httpx_mock: Any) -> None:
        api_key = "test-key"
        imdb_id = "tt0944947"

        httpx_mock.add_response(
            url=f"{CINEMETA_BASE}/meta/series/{imdb_id}.json",
            json={
                "meta": {
                    "videos": [
                        {
                            "id": f"{imdb_id}:1:1",
                            "season": 1,
                            "episode": 1,
                            "title": "E1",
                        },
                        {
                            "id": f"{imdb_id}:1:2",
                            "season": 1,
                            "episode": 2,
                            "title": "E2",
                        },
                    ],
                }
            },
        )
        httpx_mock.add_response(
            url=f"{STREMIO_BASE}/{api_key}/stream/series/{imdb_id}:1:1.json",
            json={
                "streams": [
                    {
                        "name": "TorBox (Instant) (1080p)",
                        "description": MOCK_DESC,
                        "behaviorHints": {"videoSize": 2_000_000_000},
                    }
                ]
            },
        )
        httpx_mock.add_response(
            url=f"{STREMIO_BASE}/{api_key}/stream/series/{imdb_id}:1:2.json",
            json={
                "streams": [
                    {
                        "name": "TorBox (720p)",
                        "description": MOCK_DESC,
                        "behaviorHints": {"videoSize": 1_000_000_000},
                    }
                ]
            },
        )

        result = runner.invoke(
            app,
            [
                "torrents",
                "checkcached",
                "show",
                imdb_id,
                "--season",
                "1",
                "--cached",
                "--json",
            ],
            env={"TORBOX_API_KEY": api_key},
        )
        assert result.exit_code == 0
        # Only E1 should appear because E2 is not cached
        assert "E1" in result.output
        assert "E2" not in result.output

    def test_show_episodes_filter(self, httpx_mock: Any) -> None:
        api_key = "test-key"
        imdb_id = "tt0944947"

        httpx_mock.add_response(
            url=f"{CINEMETA_BASE}/meta/series/{imdb_id}.json",
            json={
                "meta": {
                    "videos": [
                        {
                            "id": f"{imdb_id}:1:1",
                            "season": 1,
                            "episode": 1,
                            "title": "E1",
                        },
                        {
                            "id": f"{imdb_id}:1:2",
                            "season": 1,
                            "episode": 2,
                            "title": "E2",
                        },
                        {
                            "id": f"{imdb_id}:1:3",
                            "season": 1,
                            "episode": 3,
                            "title": "E3",
                        },
                    ],
                }
            },
        )
        httpx_mock.add_response(
            url=f"{STREMIO_BASE}/{api_key}/stream/series/{imdb_id}:1:1.json",
            json={"streams": []},
        )
        httpx_mock.add_response(
            url=f"{STREMIO_BASE}/{api_key}/stream/series/{imdb_id}:1:3.json",
            json={"streams": []},
        )

        result = runner.invoke(
            app,
            [
                "torrents",
                "checkcached",
                "show",
                imdb_id,
                "--season",
                "1",
                "--episodes",
                "1,3",
                "--json",
            ],
            env={"TORBOX_API_KEY": api_key},
        )
        assert result.exit_code == 0
        assert "E1" in result.output
        assert "E2" not in result.output
        assert "E3" in result.output

    def test_show_no_episodes_found(self, httpx_mock: Any) -> None:
        api_key = "test-key"
        imdb_id = "tt0944947"

        httpx_mock.add_response(
            url=f"{CINEMETA_BASE}/meta/series/{imdb_id}.json",
            json={"meta": {"videos": []}},
        )

        result = runner.invoke(
            app,
            ["torrents", "checkcached", "show", imdb_id, "--season", "1"],
            env={"TORBOX_API_KEY": api_key},
        )
        assert result.exit_code == 1
        assert "No episodes found" in result.output


class TestCheckcachedBackwardCompat:
    def test_checkcached_hashes_get(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/torrents/checkcached?hash=abc123",
            json={"success": True, "data": {}},
        )
        result = runner.invoke(
            app,
            ["torrents", "checkcached", "abc123", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "GET"

    def test_checkcached_hashes_batch(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/torrents/checkcached",
            json={"success": True, "data": {}},
        )
        result = runner.invoke(
            app,
            ["torrents", "checkcached", "abc123", "def456", "--batch", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "POST"

    def test_checkcached_hashes_explicit(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=f"{DEFAULT_BASE_URL}/torrents/checkcached?hash=abc123",
            json={"success": True, "data": {}},
        )
        result = runner.invoke(
            app,
            ["torrents", "checkcached", "hashes", "abc123", "--json"],
            env={"TORBOX_API_KEY": "dummy"},
        )
        assert result.exit_code == 0
        req = httpx_mock.get_requests()[0]
        assert req.method == "GET"
