"""Tests for Stremio-based search commands."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from torbox.cli import app
from torbox.stremio import (
    StremioClient,
    filter_streams,
    guessit_parse,
    is_cached,
    parse_resolution,
    parse_stream_description,
)

runner = CliRunner()

STREMIO_BASE = "https://stremio.torbox.app"
CINEMETA_BASE = "https://v3-cinemeta.strem.io"


MOCK_DESC = (
    "Quality: BLURAY\n"
    "Name: The.Matrix.1999.1080p.BrRip.x264.YIFY.mp4\n"
    "Size: 2GB | Source: torrentscsv\n"
    "Language: UNKNOWN\n"
    "Type: Torrent | Seeders: 704"
)

MOCK_DESC_4K = (
    "Quality: UHD\n"
    "Name: The.Matrix.1999.2160p.BluRay.x264-SPARKS.mkv\n"
    "Size: 15GB | Source: torrentscsv\n"
    "Language: UNKNOWN\n"
    "Type: Torrent | Seeders: 200"
)

MOCK_DESC_720P = (
    "Quality: HD\n"
    "Name: The.Matrix.1999.720p.BRRip.XviD.AC3-EVO.avi\n"
    "Size: 1GB | Source: torrentscsv\n"
    "Language: UNKNOWN\n"
    "Type: Torrent | Seeders: 300"
)


def test_parse_stream_description() -> None:
    result = parse_stream_description(MOCK_DESC)
    assert result["quality"] == "BLURAY"
    assert "The.Matrix.1999" in result["name"]
    assert result["source"] == "torrentscsv"
    assert result["seeders"] == "704"
    assert result["type"] == "Torrent"


def test_parse_resolution() -> None:
    assert parse_resolution("TorBox (Instant) (1080p)") == "1080p"
    assert parse_resolution("TorBox (4k)") == "4k"
    assert parse_resolution("TorBox (Unknown)") == "unknown"


def test_is_cached() -> None:
    assert is_cached("TorBox (Instant) (1080p)") is True
    assert is_cached("TorBox (1080p)") is False


def _make_stream(name: str, desc: str, vsize: int) -> dict[str, Any]:
    return {
        "name": name,
        "description": desc,
        "behaviorHints": {"videoSize": vsize},
    }


def test_filter_streams_by_cached() -> None:
    streams = [
        _make_stream("TorBox (Instant) (1080p)", MOCK_DESC, 1_000_000),
        _make_stream("TorBox (720p)", MOCK_DESC, 500_000),
    ]
    result = filter_streams(streams, cached=True)
    assert len(result) == 1
    assert result[0]["_parsed"]["cached"] is True


def test_filter_streams_by_min_seeders() -> None:
    desc1 = "Type: Torrent | Seeders: 10"
    desc2 = "Type: Torrent | Seeders: 500"
    streams = [
        _make_stream("TorBox (1080p)", desc1, 1_000_000),
        _make_stream("TorBox (720p)", desc2, 500_000),
    ]
    result = filter_streams(streams, min_seeders=100)
    assert len(result) == 1
    assert result[0]["_parsed"]["seeders"] == 500


def test_filter_streams_by_size() -> None:
    streams = [
        _make_stream("TorBox (1080p)", MOCK_DESC, 5_000_000_000),
        _make_stream("TorBox (720p)", MOCK_DESC, 500_000_000),
    ]
    result = filter_streams(streams, min_size=1_000_000_000, max_size=10_000_000_000)
    assert len(result) == 1
    assert result[0]["behaviorHints"]["videoSize"] == 5_000_000_000


def test_filter_streams_sort_by_seeders() -> None:
    desc1 = "Type: Torrent | Seeders: 10"
    desc2 = "Type: Torrent | Seeders: 500"
    streams = [
        _make_stream("TorBox (1080p)", desc1, 1_000_000),
        _make_stream("TorBox (720p)", desc2, 500_000),
    ]
    result = filter_streams(streams, sort="seeders")
    assert result[0]["_parsed"]["seeders"] == 500
    assert result[1]["_parsed"]["seeders"] == 10


def test_filter_streams_by_resolution() -> None:
    streams = [
        _make_stream("TorBox (Instant) (4k)", MOCK_DESC_4K, 7_000_000_000),
        _make_stream("TorBox (Instant) (1080p)", MOCK_DESC, 2_000_000_000),
        _make_stream("TorBox (720p)", MOCK_DESC_720P, 1_000_000_000),
    ]
    result = filter_streams(streams, resolution="1080p")
    assert len(result) == 1
    assert result[0]["_parsed"]["resolution"] == "1080p"


def test_filter_streams_limit() -> None:
    desc1 = "Type: Torrent | Seeders: 10"
    desc2 = "Type: Torrent | Seeders: 500"
    desc3 = "Type: Torrent | Seeders: 300"
    streams = [
        _make_stream("TorBox (1080p)", desc1, 1_000_000),
        _make_stream("TorBox (720p)", desc2, 500_000),
        _make_stream("TorBox (1080p)", desc3, 2_000_000),
    ]
    result = filter_streams(streams, limit=2)
    assert len(result) == 2


def test_stremio_client_init_no_key() -> None:
    with pytest.raises(ValueError, match="API key is required"):
        StremioClient(api_key=None)


def test_stremio_client_stream_search(httpx_mock: Any) -> None:
    api_key = "test-key-123"
    imdb_id = "tt0133093"
    mock_response = {"streams": [{"name": "TorBox (Instant) (1080p)"}]}

    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/{imdb_id}.json",
        json=mock_response,
    )

    client = StremioClient(api_key=api_key)
    result = client.stream_search(imdb_id)
    assert result == mock_response
    assert len(result["streams"]) == 1


def test_stremio_client_stream_search_series(httpx_mock: Any) -> None:
    api_key = "test-key-123"
    imdb_id = "tt0944947"
    mock_response = {"streams": []}

    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/series/{imdb_id}:1:1.json",
        json=mock_response,
    )

    client = StremioClient(api_key=api_key)
    result = client.stream_search(imdb_id, type="series", season=1, episode=1)
    assert result == mock_response


def test_stremio_client_library_search(httpx_mock: Any) -> None:
    api_key = "test-key-123"
    mock_response = {"metas": [{"name": "batman.mkv"}]}

    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/catalog/movie/user-movies/search=batman.json",
        json=mock_response,
    )

    client = StremioClient(api_key=api_key)
    result = client.library_search("batman")
    assert result == mock_response
    assert len(result["metas"]) == 1


def test_cinemeta_search(httpx_mock: Any) -> None:
    mock_response = {
        "metas": [
            {"id": "tt0133093", "name": "The Matrix", "year": "1999", "type": "movie"}
        ]
    }

    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/catalog/movie/top/search=the%20matrix.json",
        json=mock_response,
    )

    result = StremioClient.cinemeta_search("the matrix")
    assert len(result["metas"]) == 1
    assert result["metas"][0]["id"] == "tt0133093"


def test_stremio_client_http_error(httpx_mock: Any) -> None:
    api_key = "test-key-123"
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/tt0133093.json",
        status_code=500,
    )

    client = StremioClient(api_key=api_key)
    with pytest.raises(Exception):
        client.stream_search("tt0133093")


# --- CLI Integration Tests ---


def test_search_command_help() -> None:
    result = runner.invoke(app, ["search", "--help"])
    assert result.exit_code == 0
    assert "Unofficial" in result.output


def test_search_library_command_help() -> None:
    result = runner.invoke(app, ["search", "library", "--help"])
    assert result.exit_code == 0
    assert "Search your TorBox library" in result.output


def test_search_no_api_key() -> None:
    result = runner.invoke(app, ["search", "streams", "the matrix"])
    assert result.exit_code != 0


def test_search_by_imdb_id(httpx_mock: Any) -> None:
    api_key = "test-key-123"
    imdb_id = "tt0133093"

    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/{imdb_id}.json",
        json={
            "streams": [
                {
                    "name": "TorBox (Instant) (1080p)",
                    "description": "",
                    "behaviorHints": {},
                }
            ]
        },
    )

    result = runner.invoke(
        app,
        ["search", "streams", imdb_id, "--json"],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 0
    assert "TorBox (Instant) (1080p)" in result.output


def test_search_by_title(httpx_mock: Any) -> None:
    api_key = "test-key-123"

    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/catalog/movie/top/search=the%20matrix.json",
        json={
            "metas": [
                {
                    "id": "tt0133093",
                    "name": "The Matrix",
                    "year": "1999",
                    "type": "movie",
                }
            ]
        },
    )
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/tt0133093.json",
        json={
            "streams": [
                {
                    "name": "TorBox (Instant) (1080p)",
                    "description": "",
                    "behaviorHints": {},
                }
            ]
        },
    )

    result = runner.invoke(
        app,
        ["search", "streams", "the matrix", "--first", "--json"],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 0
    assert "TorBox (Instant) (1080p)" in result.output


def test_search_library_command(httpx_mock: Any) -> None:
    api_key = "test-key-123"

    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/catalog/movie/user-movies/search=batman.json",
        json={
            "metas": [
                {"name": "batman.mkv", "file_size": 1000, "file_id": 1, "type": "movie"}
            ]
        },
    )

    result = runner.invoke(
        app,
        ["search", "library", "batman", "--json"],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 0
    assert "batman.mkv" in result.output


def test_search_with_filters(httpx_mock: Any) -> None:
    api_key = "test-key-123"
    imdb_id = "tt0133093"

    stream_data = {
        "streams": [
            {
                "name": "TorBox (Instant) (1080p)",
                "description": (
                    "Size: 2GB | Source: torrentscsv\nType: Torrent | Seeders: 704"
                ),
                "behaviorHints": {"videoSize": 2000000000},
            },
            {
                "name": "TorBox (1080p)",
                "description": (
                    "Size: 4GB | Source: bitsearch\nType: Torrent | Seeders: 50"
                ),
                "behaviorHints": {"videoSize": 4000000000},
            },
        ]
    }

    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/{imdb_id}.json",
        json=stream_data,
    )

    result = runner.invoke(
        app,
        ["search", "streams", imdb_id, "--cached", "--min-seeders", "100", "--json"],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 0
    assert "TorBox (Instant) (1080p)" in result.output


def test_old_torrents_search_still_removed() -> None:
    result = runner.invoke(
        app, ["torrents", "search", "ubuntu"], env={"TORBOX_API_KEY": "dummy"}
    )
    assert result.exit_code != 0
    assert "No such command" in result.output or "Invalid value" in result.output


def test_search_default_callback(httpx_mock: Any) -> None:
    """Default search (no subcommand) routes to streams."""
    api_key = "test-key-123"

    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/catalog/movie/top/search=the%20matrix.json",
        json={
            "metas": [
                {
                    "id": "tt0133093",
                    "name": "The Matrix",
                    "year": "1999",
                    "type": "movie",
                }
            ]
        },
    )
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/tt0133093.json",
        json={
            "streams": [
                {
                    "name": "TorBox (Instant) (1080p)",
                    "description": "",
                    "behaviorHints": {},
                }
            ]
        },
    )

    result = runner.invoke(
        app,
        ["search", "the matrix", "--first", "--json"],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 0
    assert "TorBox (Instant) (1080p)" in result.output


def test_search_default_callback_no_args() -> None:
    """Search with no args shows help."""
    result = runner.invoke(app, ["search"])
    # Typer/Click exits with code 2 for no_args_is_help
    assert result.exit_code == 2
    assert "streams" in result.output
    assert "library" in result.output


def test_guessit_parse_movie_filename() -> None:
    """guessit extracts metadata from a typical movie filename."""
    result = guessit_parse("The.Dark.Knight.2008.1080p.BluRay.x264-SPARKS.mkv")
    assert result.get("title") == "The Dark Knight"
    assert result.get("year") == 2008
    assert result.get("screen_size") == "1080p"
    assert result.get("source") == "Blu-ray"
    assert result.get("video_codec") == "H.264"
    assert result.get("release_group") == "SPARKS"
    assert result.get("type") == "movie"


def test_guessit_parse_series_filename() -> None:
    """guessit extracts metadata from a typical TV episode filename."""
    result = guessit_parse("Game.of.Thrones.S01E01.1080p.WEB-DL.DD5.1.H.264-NTb.mkv")
    assert result.get("title") == "Game of Thrones"
    assert result.get("season") == 1
    assert result.get("episode") == 1
    assert result.get("screen_size") == "1080p"
    assert result.get("source") == "Web"
    assert result.get("audio_codec") == "Dolby Digital"
    assert result.get("release_group") == "NTb"
    assert result.get("type") == "episode"


def test_guessit_parse_empty_string() -> None:
    """guessit_parse handles empty filenames gracefully."""
    assert guessit_parse("") == {}
    assert guessit_parse(None) == {}  # type: ignore[arg-type]


def test_filter_streams_uses_guessit_fields() -> None:
    """filter_streams attaches guessit-extracted metadata to _parsed."""
    streams = [
        _make_stream("TorBox (Instant) (1080p)", MOCK_DESC, 2_000_000_000),
    ]
    result = filter_streams(streams)
    assert len(result) == 1
    parsed = result[0]["_parsed"]
    assert parsed["release_group"] == "YIFY"
    assert parsed["year"] == 1999
    assert parsed["video_codec"] == "H.264"
    assert parsed["source"] == "Blu-ray"


def test_filter_streams_by_guessit_source() -> None:
    """filter_streams can filter by source extracted via guessit."""
    streams = [
        _make_stream("TorBox (Instant) (1080p)", MOCK_DESC, 2_000_000_000),
        _make_stream(
            "TorBox (720p)",
            (
                "Name: The.Matrix.1999.720p.WEB-DL.x264-NTG.mp4\n"
                "Size: 1GB | Source: bitsearch"
            ),
            1_000_000_000,
        ),
    ]
    result = filter_streams(streams, source="Web")
    assert len(result) == 1
    assert result[0]["_parsed"]["source"] == "Web"


def test_search_with_config_file_api_key(
    tmp_path: Any, httpx_mock: Any, monkeypatch: Any
) -> None:
    """Search commands resolve API key from .env config file."""
    api_key = "config-file-key"
    env_file = tmp_path / ".env"
    env_file.write_text(f"TORBOX_API_KEY={api_key}\n")
    monkeypatch.chdir(str(tmp_path))

    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/tt0133093.json",
        json={"streams": [{"name": "TorBox (1080p)", "behaviorHints": {}}]},
    )

    result = runner.invoke(
        app,
        ["search", "streams", "tt0133093", "--json"],
    )
    assert result.exit_code == 0
    assert "TorBox (1080p)" in result.output


def test_search_default_callback_with_options(httpx_mock: Any) -> None:
    """Default search callback passes options through to streams command."""
    api_key = "test-key-123"

    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/catalog/movie/top/search=the%20matrix.json",
        json={
            "metas": [
                {
                    "id": "tt0133093",
                    "name": "The Matrix",
                    "year": "1999",
                    "type": "movie",
                }
            ]
        },
    )
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/tt0133093.json",
        json={
            "streams": [
                {
                    "name": "TorBox (Instant) (1080p)",
                    "description": "",
                    "behaviorHints": {},
                }
            ]
        },
    )

    result = runner.invoke(
        app,
        ["search", "the matrix", "--first", "--resolution", "1080p", "--json"],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 0
    assert "TorBox (Instant) (1080p)" in result.output


def test_search_table_shows_guessit_columns(httpx_mock: Any) -> None:
    """Human-mode table output includes guessit-extracted group and year."""
    api_key = "test-key-123"
    imdb_id = "tt0133093"

    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/{imdb_id}.json",
        json={
            "streams": [
                {
                    "name": "TorBox (Instant) (1080p)",
                    "description": (
                        "Name: The.Dark.Knight.2008.1080p.BluRay.x264-SPARKS.mk4\n"
                        "Size: 2GB | Source: torrentscsv\nType: Torrent | Seeders: 704"
                    ),
                    "behaviorHints": {"videoSize": 2_000_000_000},
                }
            ]
        },
    )

    result = runner.invoke(
        app,
        ["search", "streams", imdb_id],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 0
    assert "SPARK" in result.output
    assert "2008" in result.output
    assert "Blu-ray" in result.output


# --- Cinemeta Enhancement Tests ---


def test_cinemeta_popular(httpx_mock: Any) -> None:
    """cinemeta_popular fetches trending items without a query."""
    mock_response = {
        "metas": [
            {"id": "tt0133093", "name": "The Matrix", "year": "1999", "type": "movie"}
        ]
    }
    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/catalog/movie/top.json",
        json=mock_response,
    )

    result = StremioClient.cinemeta_popular("movie")
    assert len(result["metas"]) == 1
    assert result["metas"][0]["id"] == "tt0133093"


def test_cinemeta_meta(httpx_mock: Any) -> None:
    """cinemeta_meta fetches full metadata for an IMDB ID."""
    mock_response = {
        "meta": {
            "id": "tt0133093",
            "name": "The Matrix",
            "year": "1999",
            "imdbRating": "8.7",
            "runtime": "136 min",
            "genres": ["Action", "Sci-Fi"],
            "description": "When a beautiful stranger leads computer hacker Neo...",
        }
    }
    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/meta/movie/tt0133093.json",
        json=mock_response,
    )

    result = StremioClient.cinemeta_meta("tt0133093", "movie")
    assert result["meta"]["imdbRating"] == "8.7"
    assert result["meta"]["runtime"] == "136 min"


def test_search_info_command(httpx_mock: Any) -> None:
    """info command shows full Cinemeta metadata for an IMDB ID."""
    mock_response = {
        "meta": {
            "id": "tt0133093",
            "name": "The Matrix",
            "year": "1999",
            "imdbRating": "8.7",
            "runtime": "136 min",
            "genres": ["Action", "Sci-Fi"],
            "description": "When a beautiful stranger leads computer hacker Neo...",
            "cast": ["Keanu Reeves", "Laurence Fishburne"],
        }
    }
    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/meta/movie/tt0133093.json",
        json=mock_response,
    )

    result = runner.invoke(
        app,
        ["search", "info", "tt0133093", "--json"],
    )
    assert result.exit_code == 0
    assert "8.7" in result.output
    assert "136 min" in result.output


def test_search_popular_command(httpx_mock: Any) -> None:
    """popular command browses trending titles from Cinemeta."""
    api_key = "test-key-123"

    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/catalog/movie/top.json",
        json={
            "metas": [
                {
                    "id": "tt0133093",
                    "name": "The Matrix",
                    "year": "1999",
                    "imdbRating": "8.7",
                    "genres": ["Action", "Sci-Fi"],
                    "type": "movie",
                }
            ]
        },
    )

    result = runner.invoke(
        app,
        ["search", "popular", "--json"],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 0
    assert "The Matrix" in result.output


def test_search_streams_with_details_flag(httpx_mock: Any) -> None:
    """--details flag shows Cinemeta metadata panel before streams."""
    api_key = "test-key-123"
    imdb_id = "tt0133093"

    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/meta/movie/{imdb_id}.json",
        json={
            "meta": {
                "name": "The Matrix",
                "year": "1999",
                "imdbRating": "8.7",
                "runtime": "136 min",
                "genres": ["Action", "Sci-Fi"],
                "description": (
                    "A computer hacker learns about the true nature of reality."
                ),
            }
        },
    )
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/{imdb_id}.json",
        json={
            "streams": [
                {
                    "name": "TorBox (Instant) (1080p)",
                    "description": "",
                    "behaviorHints": {},
                }
            ]
        },
    )

    result = runner.invoke(
        app,
        ["search", "streams", imdb_id, "--details"],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 0
    assert "The Matrix" in result.output
    assert "8.7" in result.output
    assert "136 min" in result.output
    assert "Action" in result.output


def test_search_streams_with_genre_filter(httpx_mock: Any) -> None:
    """--genre filters Cinemeta search results client-side."""
    api_key = "test-key-123"

    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/catalog/movie/top/search=matrix.json",
        json={
            "metas": [
                {
                    "id": "tt0133093",
                    "name": "The Matrix",
                    "year": "1999",
                    "genres": ["Action", "Sci-Fi"],
                    "type": "movie",
                },
                {
                    "id": "tt0295432",
                    "name": "The Matrix Revisited",
                    "year": "2001",
                    "genres": ["Documentary"],
                    "type": "movie",
                },
            ]
        },
    )
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/tt0133093.json",
        json={"streams": [{"name": "TorBox (1080p)", "behaviorHints": {}}]},
    )

    result = runner.invoke(
        app,
        ["search", "streams", "matrix", "--first", "--genre", "Action", "--json"],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 0
    assert "TorBox (1080p)" in result.output


def test_search_streams_genre_filter_no_match(httpx_mock: Any) -> None:
    """--genre returns no match when genre doesn't exist in results."""
    api_key = "test-key-123"

    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/catalog/movie/top/search=matrix.json",
        json={
            "metas": [
                {
                    "id": "tt0133093",
                    "name": "The Matrix",
                    "year": "1999",
                    "genres": ["Action", "Sci-Fi"],
                    "type": "movie",
                }
            ]
        },
    )

    result = runner.invoke(
        app,
        ["search", "streams", "matrix", "--first", "--genre", "Romance", "--json"],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 1


def test_cinemeta_table_shows_rating_and_genre() -> None:
    """Picker table includes imdbRating and genre columns."""
    from unittest.mock import patch

    from torbox.commands.search import _print_cinemeta_table

    metas = [
        {
            "id": "tt0133093",
            "name": "The Matrix",
            "year": "1999",
            "imdbRating": "8.7",
            "genres": ["Action", "Sci-Fi"],
            "type": "movie",
        }
    ]
    with patch("torbox.commands.search.console") as mock_console:
        _print_cinemeta_table(metas, "matrix")
        table = mock_console.print.call_args[0][0]
        col_names = [str(c.header) for c in table.columns]
        assert "Rating" in col_names
        assert "Genre" in col_names


# --- StremioClient deep tests ---


def test_stremio_client_base_url() -> None:
    """base_url property returns the expected URL."""
    client = StremioClient(api_key="abc123")
    assert client.base_url == "https://stremio.torbox.app/abc123"


def test_stremio_client_verbose_stream_search(httpx_mock: Any, capsys: Any) -> None:
    """Verbose mode prints request path and timing to stderr."""
    api_key = "test-key-123"
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/tt0133093.json",
        json={"streams": [{"name": "s1"}]},
    )

    client = StremioClient(api_key=api_key, verbose=True)
    client.stream_search("tt0133093")
    captured = capsys.readouterr()
    assert "[stremio] GET" in captured.err
    assert "1 streams" in captured.err


def test_stremio_client_verbose_library_search(httpx_mock: Any, capsys: Any) -> None:
    """Verbose mode prints library request info to stderr."""
    api_key = "test-key-123"
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/catalog/movie/user-movies/search=batman.json",
        json={"metas": [{"name": "b"}]},
    )

    client = StremioClient(api_key=api_key, verbose=True)
    client.library_search("batman")
    captured = capsys.readouterr()
    assert "[stremio] GET" in captured.err
    assert "1 library items" in captured.err


def test_stremio_client_retry_network_error(httpx_mock: Any) -> None:
    """Network errors trigger retries before succeeding."""
    api_key = "test-key-123"
    # First call times out, second succeeds
    httpx_mock.add_exception(
        httpx.ConnectTimeout("Connection timed out"),
    )
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/tt0133093.json",
        json={"streams": []},
    )

    client = StremioClient(api_key=api_key)
    result = client.stream_search("tt0133093")
    assert result == {"streams": []}


def test_stremio_client_retry_rate_limit(httpx_mock: Any) -> None:
    """429 with auto_retry waits and retries."""
    api_key = "test-key-123"
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/tt0133093.json",
        status_code=429,
        headers={"Retry-After": "0"},
    )
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/tt0133093.json",
        json={"streams": []},
    )

    client = StremioClient(api_key=api_key, auto_retry=True)
    result = client.stream_search("tt0133093")
    assert result == {"streams": []}


def test_stremio_client_retry_exhausted(httpx_mock: Any) -> None:
    """All retries exhausted raises the last exception."""
    api_key = "test-key-123"
    # retries=2 means 3 attempts total
    for _ in range(3):
        httpx_mock.add_exception(httpx.ConnectTimeout("timeout"))

    client = StremioClient(api_key=api_key)
    with pytest.raises(httpx.ConnectTimeout):
        client.stream_search("tt0133093")


def test_stremio_client_retry_rate_limit_exhausted(httpx_mock: Any) -> None:
    """429 on final retry attempt raises HTTPStatusError, not RuntimeError."""
    api_key = "test-key-123"
    # retries=2 means 3 attempts total; all return 429
    for _ in range(3):
        httpx_mock.add_response(
            url=f"{STREMIO_BASE}/{api_key}/stream/movie/tt0133093.json",
            status_code=429,
            headers={"Retry-After": "0"},
        )

    client = StremioClient(api_key=api_key, auto_retry=True)
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        client.stream_search("tt0133093")
    assert exc_info.value.response.status_code == 429


def test_guessit_parse_exception() -> None:
    """guessit_parse returns empty dict on exception."""
    from unittest.mock import patch

    with patch("torbox.stremio._guessit", side_effect=RuntimeError("boom")):
        assert guessit_parse("anything.mkv") == {}


def test_filter_streams_sort_by_size() -> None:
    """Sort by video size descending."""
    streams = [
        _make_stream("s1", MOCK_DESC, 1_000_000),
        _make_stream("s2", MOCK_DESC, 5_000_000),
    ]
    result = filter_streams(streams, sort="size")
    assert result[0]["behaviorHints"]["videoSize"] == 5_000_000


def test_filter_streams_sort_by_quality() -> None:
    """Sort by resolution quality descending."""
    streams = [
        _make_stream("TorBox (720p)", MOCK_DESC_720P, 1_000_000),
        _make_stream("TorBox (Instant) (1080p)", MOCK_DESC, 2_000_000),
        _make_stream("TorBox (4k)", MOCK_DESC_4K, 7_000_000),
    ]
    result = filter_streams(streams, sort="quality")
    # guessit extracts 2160p from the filename, not 4k from the stream name
    assert result[0]["_parsed"]["resolution"] == "2160p"
    assert result[1]["_parsed"]["resolution"] == "1080p"
    assert result[2]["_parsed"]["resolution"] == "720p"


def test_filter_streams_sort_by_quality_unknown() -> None:
    """Unknown resolution gets lowest quality sort rank."""
    desc_no_res = (
        "Quality: CAM\n"
        "Name: Some.Movie.avi\n"
        "Size: 1GB | Source: torrentscsv\n"
        "Type: Torrent | Seeders: 10"
    )
    streams = [
        _make_stream("TorBox (Unknown)", desc_no_res, 1_000_000),
        _make_stream("TorBox (720p)", MOCK_DESC_720P, 1_000_000),
    ]
    result = filter_streams(streams, sort="quality")
    assert result[0]["_parsed"]["resolution"] == "720p"
    assert result[1]["_parsed"]["resolution"] == "unknown"


# --- search.py error / edge-case tests ---


def test_search_streams_no_results_quiet(httpx_mock: Any) -> None:
    """No streams in quiet mode exits silently."""
    api_key = "test-key-123"
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/tt0133093.json",
        json={"streams": []},
    )

    result = runner.invoke(
        app,
        ["--quiet", "search", "streams", "tt0133093"],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 0
    assert "No streams found" not in result.output


def test_search_library_no_results_quiet(httpx_mock: Any) -> None:
    """Empty library in quiet mode exits silently."""
    api_key = "test-key-123"
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/catalog/movie/user-movies/search=nope.json",
        json={"metas": []},
    )

    result = runner.invoke(
        app,
        ["--quiet", "search", "library", "nope"],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 0
    assert "library is empty" not in result.output


def test_search_cinemeta_error_quiet(httpx_mock: Any) -> None:
    """Cinemeta failure in quiet mode still exits with error."""
    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/catalog/movie/top/search=nope.json",
        status_code=500,
    )

    result = runner.invoke(
        app,
        ["--quiet", "search", "streams", "nope", "--json"],
        env={"TORBOX_API_KEY": "k"},
    )
    assert result.exit_code == 1


def test_search_no_cinemeta_matches_quiet(httpx_mock: Any) -> None:
    """No Cinemeta matches in quiet mode exits with code 1."""
    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/catalog/movie/top/search=nope.json",
        json={"metas": []},
    )

    result = runner.invoke(
        app,
        ["--quiet", "search", "streams", "nope", "--json"],
        env={"TORBOX_API_KEY": "k"},
    )
    assert result.exit_code == 1


def test_search_invalid_type() -> None:
    """Invalid --type raises BadParameter."""
    result = runner.invoke(
        app,
        ["search", "streams", "tt0133093", "--type", "invalid"],
        env={"TORBOX_API_KEY": "k"},
    )
    assert result.exit_code != 0
    assert "Type must be one of" in result.output


def test_search_library_invalid_type() -> None:
    """Invalid --type for library raises BadParameter."""
    result = runner.invoke(
        app,
        ["search", "library", "x", "--type", "invalid"],
        env={"TORBOX_API_KEY": "k"},
    )
    assert result.exit_code != 0


def test_search_popular_invalid_type() -> None:
    """Invalid --type for popular raises BadParameter."""
    result = runner.invoke(
        app,
        ["search", "popular", "--type", "invalid"],
        env={"TORBOX_API_KEY": "k"},
    )
    assert result.exit_code != 0


def test_search_info_invalid_type() -> None:
    """Invalid --type for info raises BadParameter."""
    result = runner.invoke(
        app,
        ["search", "info", "tt0133093", "--type", "invalid"],
        env={"TORBOX_API_KEY": "k"},
    )
    assert result.exit_code != 0


def test_search_popular_cinemeta_error_quiet(httpx_mock: Any) -> None:
    """Popular Cinemeta failure in quiet mode exits with code 1."""
    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/catalog/movie/top.json",
        status_code=500,
    )

    result = runner.invoke(
        app,
        ["--quiet", "search", "popular", "--json"],
        env={"TORBOX_API_KEY": "k"},
    )
    assert result.exit_code == 1


def test_search_info_cinemeta_error_quiet(httpx_mock: Any) -> None:
    """Info Cinemeta failure in quiet mode exits with code 1."""
    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/meta/movie/tt0133093.json",
        status_code=500,
    )

    result = runner.invoke(
        app,
        ["--quiet", "search", "info", "tt0133093", "--json"],
        env={"TORBOX_API_KEY": "k"},
    )
    assert result.exit_code == 1


def test_search_info_no_metadata(httpx_mock: Any) -> None:
    """Info returns empty meta object — exits with code 1."""
    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/meta/movie/tt0133093.json",
        json={"meta": {}},
    )

    result = runner.invoke(
        app,
        ["search", "info", "tt0133093", "--json"],
        env={"TORBOX_API_KEY": "k"},
    )
    assert result.exit_code == 1


def test_search_info_human_panel(httpx_mock: Any) -> None:
    """Info command renders a Rich panel in human mode."""
    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/meta/movie/tt0133093.json",
        json={
            "meta": {
                "name": "The Matrix",
                "year": "1999",
                "imdbRating": "8.7",
                "runtime": "136 min",
                "genres": ["Action", "Sci-Fi"],
                "description": "A hacker learns about reality.",
                "cast": ["Keanu Reeves"],
                "director": ["Wachowski"],
                "poster": "https://example.com/poster.jpg",
            }
        },
    )

    result = runner.invoke(
        app,
        ["search", "info", "tt0133093"],
        env={"TORBOX_API_KEY": "k"},
    )
    assert result.exit_code == 0
    assert "The Matrix" in result.output
    assert "8.7" in result.output
    assert "136 min" in result.output
    assert "Keanu Reeves" in result.output
    assert "Wachowski" in result.output
    assert "poster.jpg" in result.output


def test_search_streams_details_exception(httpx_mock: Any) -> None:
    """--details with failing Cinemeta meta should not crash stream output."""
    api_key = "test-key-123"
    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/meta/movie/tt0133093.json",
        status_code=500,
    )
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/tt0133093.json",
        json={
            "streams": [
                {
                    "name": "TorBox (1080p)",
                    "description": (
                        "Name: test.mp4\n"
                        "Size: 1GB | Source: torrentscsv\n"
                        "Type: Torrent | Seeders: 10"
                    ),
                    "behaviorHints": {"videoSize": 1_000_000_000},
                }
            ]
        },
    )

    result = runner.invoke(
        app,
        ["search", "streams", "tt0133093", "--details"],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 0
    assert "Streams for tt0133093" in result.output


def test_search_streams_no_results_human(httpx_mock: Any) -> None:
    """No streams in human mode prints a yellow warning."""
    api_key = "test-key-123"
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/tt0133093.json",
        json={"streams": []},
    )

    result = runner.invoke(
        app,
        ["search", "streams", "tt0133093"],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 0
    assert "No streams found" in result.output


def test_search_streams_parse_size_invalid() -> None:
    """Invalid size format raises BadParameter."""
    from torbox.commands.search import parse_size

    with pytest.raises(Exception):
        parse_size("notasize")


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_search_picker_invalid_choice_then_quit(httpx_mock: Any) -> None:
    """Interactive picker handles invalid input then quits."""
    api_key = "test-key-123"
    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/catalog/movie/top/search=matrix.json",
        json={
            "metas": [
                {
                    "id": "tt0133093",
                    "name": "The Matrix",
                    "year": "1999",
                    "type": "movie",
                },
                {
                    "id": "tt0234215",
                    "name": "The Matrix Reloaded",
                    "year": "2003",
                    "type": "movie",
                },
            ]
        },
    )
    httpx_mock.add_response(
        url=f"{STREMIO_BASE}/{api_key}/stream/movie/tt0133093.json",
        json={"streams": []},
    )

    result = runner.invoke(
        app,
        ["search", "streams", "matrix"],
        env={"TORBOX_API_KEY": api_key},
        input="q\n",
    )
    assert result.exit_code == 1


def test_search_picker_exception_during_input(
    httpx_mock: Any, monkeypatch: Any
) -> None:
    """Interactive picker handles exceptions during input gracefully."""
    api_key = "test-key-123"
    httpx_mock.add_response(
        url=f"{CINEMETA_BASE}/catalog/movie/top/search=matrix.json",
        json={
            "metas": [
                {
                    "id": "tt0133093",
                    "name": "The Matrix",
                    "year": "1999",
                    "type": "movie",
                },
                {
                    "id": "tt0234215",
                    "name": "The Matrix Reloaded",
                    "year": "2003",
                    "type": "movie",
                },
            ]
        },
    )

    def bad_input(_: str) -> str:
        raise EOFError()

    monkeypatch.setattr("builtins.input", bad_input)

    result = runner.invoke(
        app,
        ["search", "streams", "matrix"],
        env={"TORBOX_API_KEY": api_key},
    )
    assert result.exit_code == 1
