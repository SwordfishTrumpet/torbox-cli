# TorBox CLI — Agent Instructions

## Project Overview

A full-featured Python CLI wrapper for the TorBox API (https://api.torbox.app/v1), designed for both human users and LLM agents. The tool exposes every public API endpoint as a well-structured subcommand with comprehensive help, JSON output mode for programmatic consumption, and robust error handling.

## Technology Stack

- **Language:** Python 3.10+
- **CLI Framework:** [Typer](https://typer.tiangolo.com/) — community standard, type-hint driven, auto-generates help
- **HTTP Client:** `httpx` — modern, async-capable, timeout handling
- **Data Validation:** `pydantic` — models all API request/response schemas
- **Output Formatting:** `rich` — beautiful tables, progress spinners, JSON pretty-printing
- **Environment:** `python-dotenv` — `.env` file support for API keys
- **Configuration:** XDG Base Directory spec (`~/.config/torbox-cli/`)

## Architecture

```
torbox/
├── __init__.py
├── cli.py              # Main Typer app, global flags (--json, --api-key, --config)
├── client.py           # HTTP client: auth, retries, rate-limit awareness
├── config.py           # Config loader (.env, config file, CLI overrides)
├── models.py           # Pydantic models for all API schemas
├── formatters.py       # Human-readable + JSON output formatters
├── exceptions.py       # Custom exception hierarchy
├── commands/
│   ├── __init__.py
│   ├── torrents.py     # All /torrents/* endpoints
│   ├── usenet.py       # All /usenet/* endpoints
│   ├── webdl.py        # All /webdl/* endpoints
│   ├── general.py      # Status, stats, changelogs, speedtest
│   ├── user.py         # User data, settings, transactions, auth
│   ├── rss.py          # RSS feeds & items management
│   ├── queued.py       # Queued downloads
│   └── stream.py       # Video streaming
└── utils.py            # Helpers (size formatting, date parsing, etc.)
```

## Key Design Decisions

### 1. LLM-First Output
Every command supports `--json` / `-j` to emit raw API response JSON (with optional jq-like filtering via `--field`). This is the primary mode for LLM agents. Human mode uses `rich` tables and formatted strings.

### 2. Configuration Hierarchy (highest wins)
1. CLI flag: `--api-key KEY`
2. Environment variable: `TORBOX_API_KEY`
3. `.env` file in current directory
4. `~/.config/torbox-cli/config.env`
5. `~/.torbox-cli.env` (legacy fallback)

### 3. Help & Documentation
- All commands, subcommands, and options have detailed `help=` strings
- `torbox --help` shows top-level help
- `torbox torrents --help` shows group help
- `torbox torrents create --help` shows command help
- Man page generation via `torbox docs --man` (outputs troff or delegates to `help2man`)

### 4. Error Handling
- Map all TorBox error codes to typed exceptions
- Human mode: colored, actionable error messages
- JSON mode: `{"success": false, "error": "CODE", "detail": "..."}`
- Non-zero exit codes for all failures

### 5. Rate Limiting
- Client tracks 429 responses and suggests backoff
- Optional: proactive rate-limit bucket tracking

## File Conventions

- Use `ruff` for linting and formatting
- Use `mypy --strict` for type checking
- All public functions typed; `from __future__ import annotations`
- Docstrings in Google style

## Git Hygiene

**CRITICAL:** The following files are tracked locally but MUST NOT be pushed to GitHub:
- `TRD.md`
- `TODO.md`
- `AGENTS.md`
- `.env` (already in `.gitignore`)
- Any file containing secrets

The repository will eventually be made public. Before going public, verify no local-only files or secrets are in the git history.

## Build & Distribution

- `pyproject.toml` with `hatchling` build backend
- Entry point: `torbox = torbox.cli:app`
- Published to PyPI as `torbox-cli`
- Homebrew formula generated via `homebrew-pypi-poet` or manually

## Testing Strategy

- `pytest` with `pytest-httpx` for HTTP mocking
- `typer.testing.CliRunner` for CLI integration tests
- Mock API responses stored as JSON fixtures

## Commands Reference (Full API Coverage)

### Torrents
- `torbox torrents list` — GET /torrents/mylist
- `torbox torrents info <id>` — GET /torrents/mylist?id={id}
- `torbox torrents create <magnet|file>` — POST /torrents/createtorrent
- `torbox torrents control <id> --operation delete|pause|resume` — POST /torrents/controltorrent
- `torbox torrents checkcached <hash>...` — GET /torrents/checkcached
- `torbox torrents requestdl <id> --file-id <n>` — GET /torrents/requestdl
- `torbox torrents export <id>` — export .torrent file
- `torbox torrents search <query>` — search (if available)

### Usenet
- `torbox usenet list` — list downloads
- `torbox usenet create <nzb>` — POST /usenet/createusenetdownload
- `torbox usenet control <id> --operation delete|pause|resume` — POST /usenet/controlusenetdownload
- `torbox usenet requestdl <id> --file-id <n>` — GET /usenet/requestdl

### Web Downloads
- `torbox webdl list`
- `torbox webdl create <link>` — POST /webdl/createwebdownload
- `torbox webdl control <id> --operation delete|pause|resume` — POST /webdl/controlwebdownload
- `torbox webdl edit <id>` — PUT /webdl/editwebdownload
- `torbox webdl hosters` — GET /webdl/hosters

### General
- `torbox general status` — GET /
- `torbox general stats` — GET /stats
- `torbox general changelogs` — GET /changelogs/json
- `torbox general speedtest` — GET /speedtest

### User
- `torbox user me` — GET user data
- `torbox user settings` — GET / PUT settings
- `torbox user searchengines` — GET / manage search engines
- `torbox user transactions` — GET transactions
- `torbox user transaction-pdf <id>` — GET PDF
- `torbox user confirmation` — GET confirmation code
- `torbox user auth-device-start` — GET device code flow

### RSS
- `torbox rss list` — GET /rss/getfeeds
- `torbox rss items <feed-id>` — GET /rss/getfeeditems
- `torbox rss create|edit|delete` — management commands

### Queued
- `torbox queued list` — GET /queued/getqueued
- `torbox queued control` — POST /queued/controlqueued

### Stream
- `torbox stream create <id> --type torrent|usenet|webdownload` — GET /stream/createstream
- `torbox stream data <token>` — GET /stream/getstreamdata

## Global Flags

- `--api-key, -k` — override API key
- `--json, -j` — output raw JSON (LLM mode)
- `--field, -f` — extract specific field from JSON (e.g. `-f data.0.name`)
- `--config` — path to custom config file
- `--quiet, -q` — suppress non-essential output
- `--verbose, -v` — debug logging
- `--version` — show version

## Success Criteria

1. Every documented TorBox API v1 endpoint has a corresponding CLI command
2. `--help` is comprehensive and accurate at every level
3. `--json` output is valid JSON suitable for LLM parsing
4. Authentication works via `.env`, env var, or CLI flag seamlessly
5. Exit codes are meaningful (0=success, 1=general error, 2=auth error, 3=API error, etc.)
6. No secrets or local planning files leak to the public repository
