# torbox-cli

A full-featured Python CLI wrapper for the [TorBox API v1](https://torbox.app).

> **Legal Disclaimer:** This project is an **unofficial, third-party, open-source command-line interface** for the TorBox API. It is **not affiliated with, endorsed by, sponsored by, or connected to TorBox** or its parent/operating entities in any capacity. The name "TorBox" and any associated trademarks are the property of their respective owners. This tool is provided "as is" without warranty of any kind, express or implied. Use of this CLI is at your own risk and subject to the TorBox Terms of Service and API usage policies.

## Installation

```bash
pipx install torbox-cli
```

Or with `uv`:

```bash
uv tool install torbox-cli
```

## Requirements

- **Python 3.10+**
- Optional: `guessit` (bundled) for rich torrent filename parsing

## Quick Start

```bash
export TORBOX_API_KEY=your-key

# Check version and auth
torbox --version
torbox general status --json

# Enable shell completion
source <(torbox --show-completion bash)   # bash
source <(torbox --show-completion zsh)    # zsh
torbox --install-completion fish          # fish

# List your torrents
torbox torrents list
```

## Why torbox-cli?

You already use the TorBox web UI to manage downloads. But every time you want to automate a workflow, integrate with a media server, or run a cron job, you're back to writing fragile curl scripts by hand.

**torbox-cli** is the missing piece: a composable, scriptable interface to your entire TorBox account. Search for content, add downloads, monitor progress, and extract results — all from the command line, ready to pipe into your existing toolchain.

## What You Can Do

### Automate Your Entire Workflow
- **Search → Add → Monitor** without opening a browser. Search torrent streams by title or IMDB ID, filter by quality and cache status, and add them directly to your queue.
- **Rich, human-readable output** when you're exploring, **machine-readable JSON** when you're scripting.
- **Preview every destructive action** with `--dry-run` before you commit.

### Integrate Into Any Pipeline
- **Structured JSON envelopes** via `--json` / `-j` — predictable output for `jq`, `xargs`, and LLM agents.
- **Pluck nested fields** with `--field` so you never write `jq '.data[0].name'` by hand.
- **Single-line JSON** with `--compact` for streaming through GNU parallel and other line-oriented tools.
- **Pagination** (`--offset`, `--limit`) for iterating through massive datasets reliably.

### Run Reliably in Production
- **Auto-retry with exponential backoff** on rate limits — your cron jobs don't die at 2 AM because of a 429.
- **Flexible auth** that adapts to any environment: CLI flag, env var, `.env` file, or XDG config profiles.
- **Multi-account support** via INI-style profiles — switch accounts mid-script for batch operations across plans.
- **Request observability** with `--verbose` / `-v` — full headers, timing, and retry logging when things go wrong.
- **Config doctor** (`torbox config doctor`) exposes exactly which auth source is active and why.

### Developer Experience
- **Tab-complete everything** — full shell completion for bash, zsh, and fish.
- **Offline docs** — generate man pages with `torbox docs --man`.
- **Every TorBox v1 endpoint** exposed as an intuitive subcommand.

## In Practice

```bash
# One-liner: find cached 1080p streams, sort by seeders, pipe to jq
torbox search streams "inception" --resolution 1080p --cached --sort seeders --json --compact | jq '.name'

# Batch-create torrents from a file without surprises
cat magnets.txt | xargs -I {} torbox torrents create {} --dry-run

# Multi-profile automation: switch accounts mid-script
torbox --profile work torrents list --json --field data

# Cron-safe: auto-retry with backoff so rate limits don't kill nightly jobs
torbox torrents list --auto-retry --json --quiet > /var/log/torbox-backup.json

# Debug a failing command in one flag
torbox general status --verbose

# Inspect why auth isn't resolving where you expect
torbox config doctor
```

## Command Overview

| Group | Commands |
|-------|----------|
| `general` | status, stats, changelogs, speedtest |
| `search` | streams, library, popular, info |
| `torrents` | list, info, create, control, checkcached (hashes, show), requestdl, export, async-create, edit |
| `usenet` | list, create, control, edit, checkcached, requestdl |
| `webdl` | list, create, control, edit, checkcached, hosters |
| `user` | me, transactions, transaction-pdf, settings, searchengines, auth-device-start, confirmation |
| `rss` | list, items, create, edit, delete |
| `queued` | list, control |
| `stream` | create, data |
| `notifications` | list, rss, test, clear |
| `integrations` | jobs, cancel |

Run `torbox --help` or `torbox <group> --help` for detailed usage and examples.

## Search (Stremio Addon — Unofficial)

The `search` group uses TorBox's **Stremio addon endpoints** to find torrent streams and browse metadata. These are unofficial endpoints that may change without notice.

> **Note:** Search requires a TorBox API key. Configure it via `TORBOX_API_KEY`, `--api-key`, or a config file.

### Commands

| Command | Description |
|---------|-------------|
| `streams` | Search torrent streams by title or IMDB ID |
| `library` | Search your TorBox library by filename |
| `popular` | Browse popular/trending titles from Cinemeta |
| `info` | Show full metadata (plot, rating, cast, etc.) for an IMDB ID |

### `streams` — Search Torrent Streams

Search for torrent streams by **title** (auto-resolved via Cinemeta) or **direct IMDB ID**.

```bash
# Search by title (interactive Cinemeta picker)
torbox search streams "the matrix"

# Search by IMDB ID directly
torbox search streams tt0133093

# Series with season/episode
torbox search streams tt0944947 --season 1 --episode 1
torbox search streams tt0944947:1:1          # colon notation shorthand
```

#### Stream Filtering Flags

| Flag | Description | Example |
|------|-------------|---------|
| `-t, --type` | Content type: `movie`, `series`, `anime` | `--type series` |
| `-s, --season` | Season number (series only) | `--season 2` |
| `-e, --episode` | Episode number (series only) | `--episode 5` |
| `--first` | Auto-select first Cinemeta match (skip interactive) | `--first` |
| `--resolution` | Filter by resolution: `1080p`, `720p`, `4k`, etc. | `--resolution 1080p` |
| `--cached` | Only show cached (Instant) streams | `--cached` |
| `--not-cached` | Only show non-cached streams | `--not-cached` |
| `--min-size` | Minimum file size | `--min-size 1GB` |
| `--max-size` | Maximum file size | `--max-size 10GB` |
| `--min-seeders` | Minimum seeders count | `--min-seeders 50` |
| `--quality` | Filter by quality tag (e.g., `BLURAY`, `WEB-DL`) | `--quality BLURAY` |
| `--source` | Filter by source (e.g., `Blu-ray`, `Web`) | `--source Web` |
| `--sort` | Sort by: `seeders`, `size`, `quality` | `--sort seeders` |
| `--limit` | Max results to display (default: 20) | `--limit 50` |
| `--genre` | Filter Cinemeta results by genre (see list below) | `--genre Action` |
| `--details` | Show metadata panel (rating, runtime, plot) before streams | `--details` |
| `-j, --json` | Output raw JSON | `--json` |
| `-f, --field` | Extract specific field from JSON | `--field streams.0.name` |

#### Examples

```bash
# High-quality cached streams only
torbox search streams tt0133093 --resolution 1080p --cached --sort seeders

# Big files with lots of seeders
torbox search streams "interstellar" --first --min-size 5GB --min-seeders 100

# Auto-resolve title, filter by genre, show metadata
torbox search streams "action movie" --first --genre Action --details

# JSON output for scripting
torbox search streams tt0133093 --json --field streams
```

### `library` — Search Your TorBox Library

Search files already in your TorBox library by filename or partial name.

```bash
# Search library for a file
torbox search library "batman"

# JSON output
torbox search library "batman" --json
```

### `popular` — Browse Trending Titles

Browse popular movies or series from Cinemeta without a search query. After showing results, pick a number to auto-search streams for that title.

```bash
# Browse popular movies (interactive)
torbox search popular

# Popular series, limit to 5 results
torbox search popular --type series --limit 5

# JSON output (no interactive prompt)
torbox search popular --json
```

### `info` — Full Metadata Lookup

Show detailed metadata for any IMDB ID: description, rating, runtime, genres, cast, director, and poster.

```bash
# Show metadata for a movie
torbox search info tt0133093

# Metadata for a series
torbox search info tt0944947 --type series

# JSON output for further processing
torbox search info tt0133093 --json
```

### Stream Table Columns

Human-mode stream output includes rich metadata extracted from torrent filenames via `guessit`:

- **Filename** — Torrent filename (truncated if long)
- **Quality** — Quality tag from stream description
- **Size** — File size in human-readable format
- **Seeders** — Number of seeders
- **Source** — Source type (Blu-ray, Web, etc.)
- **Group** — Release group (e.g., YIFY, SPARKS, NTb)
- **Year** — Release year extracted from filename
- **Cached** — Checkmark if cached on TorBox

### Default Shortcut

`torbox search <query>` without a subcommand defaults to `streams`:

```bash
torbox search "the matrix"          # same as: torbox search streams "the matrix"
torbox search tt0133093 --cached     # same as: torbox search streams tt0133093 --cached
```

### Important Notes

- **Unofficial endpoints:** The Stremio addon endpoints are not part of the official TorBox REST API and may change.
- **Cinemeta dependency:** Title resolution requires `v3-cinemeta.strem.io` to be available. If it's down, use an IMDB ID directly.
- **Cinemeta results may vary:** Metadata availability, accuracy, and completeness depend on a third-party service outside our control.
- **No results:** If no streams are found, try broadening filters or searching without them.
- **Series without season/episode:** Some streams may work without specifying season/episode, but most require them.

> See [DISCLAIMER.md](DISCLAIMER.md) for full legal and third-party service disclaimers.

## TV Show Cache Checking (`torrents checkcached show`)

Check cache status for **all episodes of a TV show** in a single command. This discovers episodes via Cinemeta, then queries the TorBox Stremio addon for each episode in parallel, and aggregates the results into a single table.

```bash
# Check all episodes of Season 1
 torbox torrents checkcached show tt0944947 --season 1

# Only check specific episodes
 torbox torrents checkcached show tt0944947 --season 1 --episodes 1,2,3

# Filter to only cached episodes
 torbox torrents checkcached show tt0944947 --season 1 --cached

# JSON output for scripting
 torbox torrents checkcached show tt0944947 --season 1 --json

# Sort by best quality
 torbox torrents checkcached show tt0944947 --season 1 --sort quality
```

### Notes

- Uses **parallel requests** (`--max-workers` controls concurrency, default 5).
- Supports all standard stream filters: `--resolution`, `--cached/--not-cached`, `--min-seeders`, `--quality`, `--source`, `--min-size`, `--max-size`.
- Backward compatible: `torbox torrents checkcached hash1 hash2` still works (defaults to `hashes` subcommand).

### `--genre` Filter — Valid Genres

The `--genre` flag filters Cinemeta search results client-side. Genres come from IMDB/OMDb metadata. Common genres include:

- `Action`, `Adventure`, `Animation`
- `Biography`, `Comedy`, `Crime`
- `Documentary`, `Drama`
- `Family`, `Fantasy`
- `History`, `Horror`
- `Music`, `Musical`, `Mystery`
- `Romance`
- `Sci-Fi`, `Sport`
- `Thriller`
- `War`, `Western`

Use exact case-insensitive matching: `--genre "Sci-Fi"`, `--genre action`, and `--genre ACTION` all work.

### `--details` Flag

`--details` is a boolean flag (no value needed). When present, it fetches full Cinemeta metadata for the resolved IMDB ID and displays a rich panel with:
- Title and year
- IMDB rating
- Runtime
- Genres
- Plot description (truncated to ~200 chars)

This appears **before** the stream results table. It has no effect with `--json` or `--field`.

## Profiles (Multiple Accounts)

Create an INI-style config at `~/.config/torbox-cli/config.env`:

```ini
[default]
TORBOX_API_KEY = tb-your-default-key

[work]
TORBOX_API_KEY = tb-your-work-key
TORBOX_TIMEOUT = 60
```

Select a profile with `torbox --profile work torrents list`.

## Architecture

```
Command (typer) → Helpers → Client (httpx) → API
                              ↓
                      Formatters (rich / JSON)
```

The CLI follows a layered design: Typer commands validate input, the client handles auth/retries/error mapping, and formatters produce either rich tables for humans or normalized JSON envelopes for machines.

## Troubleshooting

Use `torbox config doctor` to inspect which auth source is active and what the effective values are.

| Exit Code | Meaning |
|-----------|---------|
| 1 | General / validation error |
| 2 | Authentication failure |
| 3 | API / server error |
| 4 | Rate limited |
| 5 | Plan restricted |
| 6 | Not found |
| 130 | Interrupted (Ctrl-C) |

## Contributing

1. `uv sync` — install dependencies.
2. `pre-commit install` — enable git hooks.
3. Add the Pydantic model to `torbox/models.py`.
4. Add the CLI command to `torbox/commands/*.py` with real-world `help=` text.
5. Add tests in `tests/test_<group>.py`.
6. Run `uv run ruff check torbox/ tests/` and `uv run mypy --strict torbox/`.
7. Run `uv run pytest tests/` (coverage threshold: 65%).

## See Also

- [DISCLAIMER.md](DISCLAIMER.md) — legal disclaimer and third-party service notices
- [CHANGELOG.md](CHANGELOG.md) — version history and release notes
- [TorBox API Documentation](https://torbox.app/)
- [TorBox Terms of Service](https://torbox.app/terms)
- Install: `pip install git+https://github.com/SwordfishTrumpet/torbox-cli.git`

## License

MIT
