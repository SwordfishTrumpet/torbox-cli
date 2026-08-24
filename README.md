# torbox-cli

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg)](https://github.com/astral-sh/ruff)
[![Typed: mypy](https://img.shields.io/badge/typed-mypy%20--strict-0395DE.svg)](https://mypy-lang.org/)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC.svg)](https://docs.pytest.org/)
[![Coverage](https://img.shields.io/badge/coverage-%3E%3E%2065%25-yellow.svg)](pyproject.toml)

A full-featured Python CLI wrapper for the [TorBox API v1](https://torbox.app) — manage torrents, usenet downloads, web downloads, RSS feeds, and more, directly from your terminal.

> **Legal Disclaimer:** This project is an **unofficial, third-party, open-source command-line interface** for the TorBox API. It is **not affiliated with, endorsed by, sponsored by, or connected to TorBox** or its parent/operating entities in any capacity. The name "TorBox" and any associated trademarks are the property of their respective owners. This tool is provided "as is" without warranty of any kind, express or implied. Use of this CLI is at your own risk and subject to the TorBox Terms of Service and API usage policies.

---

## About

You already use the TorBox web UI to manage downloads. But every time you want to automate a workflow, integrate with a media server, or run a cron job, you're back to writing fragile curl scripts by hand.

**torbox-cli** is the missing piece: a composable, scriptable interface to your entire TorBox account. Add torrents, monitor progress, check cache status, manage RSS feeds, export files, and extract results — all from the command line, ready to pipe into your existing toolchain.

### Core Features

- **Full TorBox v1 API coverage** — torrents, usenet, web downloads, RSS, queued downloads, streaming, notifications, integrations, and user account management
- **Dual output modes** — rich, human-readable tables and panels for interactive use; structured JSON envelopes for `jq`, `xargs`, and LLM agents
- **Dot-path field extraction** (`--field`) — pluck nested fields from API responses without writing custom parsers
- **Compact JSON mode** (`--compact`) — single-line JSON for streaming through line-oriented tools like GNU parallel
- **Auto-retry with exponential backoff** — your cron jobs survive 429 rate limits automatically
- **Multi-source authentication** — CLI flag, environment variable, `.env` file, XDG config, or INI-style profiles for multi-account workflows
- **Dry-run preview** (`--dry-run`) — preview every destructive mutation before committing
- **Request observability** (`--verbose` / `-v`) — full request/response timing and diagnostic logging to stderr
- **Config doctor** (`torbox config doctor`) — inspect exactly which auth source is active and why
- **Shell completions** — bash, zsh, and fish tab-completion out of the box
- **Offline man pages** (`torbox docs --man`) — generate troff man pages for offline reference
- **Live TUI monitor** (`torbox monitor`) — htop-style real-time dashboard across all download categories
- **Pagination** (`--offset`, `--limit`) — iterate through large datasets reliably

---

## Architecture & Tech Stack

```
Command (typer) → Helpers → Client (httpx) → API
                              ↓
                      Formatters (rich / JSON)
```

The CLI follows a layered design:

| Layer | Role | Key Libraries |
|---|---|---|
| **CLI** | Command definitions, argument parsing, input validation | [typer](https://typer.tiangolo.com/) 0.25+, [click](https://click.palletsprojects.com/) 8.0+ |
| **Client** | HTTP transport, authentication, retry logic, rate-limit handling | [httpx](https://www.python-httpx.org/) 0.28+ |
| **Models** | Request/response schema validation | [pydantic](https://docs.pydantic.dev/) 2.13+ |
| **Formatters** | Human-readable (rich) and machine-readable (JSON) output | [rich](https://rich.readthedocs.io/) 15.0+ |
| **Config** | Hierarchical config loading with multi-profile support | [python-dotenv](https://github.com/theskumar/python-dotenv) 1.2+ |

**Runtime requirements:** Python 3.10+
**Optional:** `guessit` (bundled) for rich torrent filename parsing

---

## Getting Started

### Prerequisites

- Python 3.10 or later
- A [TorBox](https://torbox.app) account with an API key

### Installation

```bash
pipx install torbox-cli
```

Or with `uv`:

```bash
uv tool install torbox-cli
```

### Verify Installation

```bash
torbox --version
torbox general status --json
```

### Configure Your API Key

Set your API key using one of these methods (listed in priority order):

**1. CLI flag** (highest priority):

```bash
torbox --api-key tb-your-key torrents list
```

**2. Environment variable:**

```bash
export TORBOX_API_KEY=tb-your-key
torbox torrents list
```

**3. `.env` file** in the current directory:

```bash
echo "TORBOX_API_KEY=tb-your-key" > .env
chmod 600 .env
torbox torrents list
```

**4. XDG config file** at `~/.config/torbox-cli/config.env`:

```bash
mkdir -p ~/.config/torbox-cli
echo "TORBOX_API_KEY=tb-your-key" > ~/.config/torbox-cli/config.env
chmod 600 ~/.config/torbox-cli/config.env
```

**5. Legacy config** at `~/.torbox-cli.env`.

**6. INI-style profiles** (lowest priority, see [profiles](#profiles-multiple-accounts) below).

> **Tip:** Run `torbox config doctor` at any time to inspect which auth source is active.

### Enable Shell Completion

```bash
source <(torbox --show-completion bash)   # bash
source <(torbox --show-completion zsh)    # zsh
torbox --install-completion fish          # fish
```

---

## Usage & Configuration

### Command Overview

| Group | Commands |
|-------|----------|
| `general` | status, stats, changelogs, speedtest |
| `torrents` | list, info, files, create, control, checkcached (hashes), requestdl, export, exportdata, async-create, edit |
| `usenet` | list, create, async-create, control, requestdl, export, edit, checkcached |
| `webdl` | list, create, async-create, control, edit, requestdl, checkcached, hosters |
| `user` | me, transactions, transaction-pdf, settings, searchengines, auth-device-start, auth-device-token, confirmation |
| `rss` | list, items, create, edit, delete |
| `queued` | list, control |
| `stream` | create, data |
| `notifications` | list, rss, test, clear |
| `monitor` | htop-style live TUI dashboard (torrents, usenet, webdl, queued) |
| `integrations` | jobs, cancel |

Run `torbox --help` or `torbox <group> --help` for detailed usage and examples.

### API Coverage Notes

- **Intentionally not implemented:** `/torrents/getqueued` and `/torrents/controlqueued`
  were deprecated by TorBox v6.2 — the live API returns `HTTP 410 DEPRECATED` for
  them (error code `DEPRECATED`, "use /v1/api/queued/getqueued instead"). Use
  `torbox queued list` / `torbox queued control` instead.
- **Note:** `https://api.torbox.app/openapi.json` still lists the legacy routes even
  though they respond with 410 — audit coverage against the live server, not just
  the spec.
- **No `queued add`:** there is no route to add a queued download. Create queued
  items directly by passing `--as-queued` to `torrents create`, `torrents async-create`,
  `webdl create`, or `webdl async-create`.

### Global Flags

These flags are available on every command and must be placed **before** the subcommand:

```bash
torbox --json torrents list          # JSON output
torbox --field data.data.0.name torrents list  # Extract nested field
torbox --compact --json torrents list    # Single-line JSON
torbox --verbose torrents list       # Request diagnostics to stderr
torbox --quiet torrents list         # Suppress human output
torbox --auto-retry torrents list    # Auto-retry on 429 rate limits
torbox --profile work torrents list  # Use named profile
torbox --api-key tb-key torrents list    # Override API key
```

### Common Workflows

```bash
# List your torrents (human-readable)
torbox torrents list

# List torrents as JSON, pipe to jq
torbox torrents list --json | jq '.data.data[].name'

# Extract a single field from the first result
torbox --field data.data.0.name --compact --json torrents list

# Filter by status with pagination
torbox torrents list --status completed --limit 10 --offset 0

# Show detailed info for a specific torrent
torbox torrents info 42

# List files within a torrent
torbox torrents files 42

# Create a torrent from a magnet link (dry-run first)
torbox torrents create --magnet 'magnet:?xt=urn:btih:...' --dry-run
torbox torrents create --magnet 'magnet:?xt=urn:btih:...'

# Create a torrent from a .torrent file
torbox torrents create --file ./ubuntu.torrent --name "Ubuntu ISO"

# Asynchronous create (errors delivered via notifications)
torbox torrents async-create --magnet 'magnet:?xt=urn:btih:...'

# Control torrents (delete, pause, resume)
torbox torrents control 42 --operation delete --yes
torbox torrents control --operation pause --all

# Edit torrent metadata
torbox torrents edit 42 --name "New Name" --tags "linux,iso"

# Check if hashes are cached on TorBox
torbox torrents checkcached hashes a1b2c3d4e5f6a7b8c9d0

# Check multiple hashes via POST (unlimited)
torbox torrents checkcached hashes hash1 hash2 hash3 --batch

# Export a .torrent file
torbox torrents export 42 --output movie.torrent

# Request a download link for a specific file
torbox torrents requestdl 42 1

# Batch-create torrents from a file (dry-run first)
cat magnets.txt | xargs -I {} torbox torrents create {} --dry-run

# Check API status (public endpoint, no auth needed)
torbox general status
torbox general status --json

# View service statistics
torbox general stats --json

# Browse recent changelogs
torbox general changelogs
torbox general changelogs --format rss

# Run a speed test
torbox general speedtest --test-length short --region us

# User account information
torbox user me
torbox user me --json

# View and manage search engines
torbox user searchengines

# User settings
torbox user settings --json
torbox user settings --body '{"theme": "dark"}'

# View transactions
torbox user transactions --limit 5

# Download transaction invoice PDF
torbox user transaction-pdf 123 --output invoice.pdf

# Device authentication flow (no API key needed)
# Step 1: start the flow, receive a device code
# Step 2: user verifies the code in the browser, then exchange it for an API token
torbox user auth-device-start
torbox user auth-device-token dc123

# Manage RSS feeds
torbox rss list
torbox rss create https://example.com/feed.xml --name "My Feed" --type torrent
torbox rss edit 2 --name "Updated Feed"
torbox rss items 2
torbox rss delete 2 --yes

# Manage usenet downloads
torbox usenet list --limit 10
torbox usenet create https://example.com/file.nzb --name "My NZB"
torbox usenet async-create https://example.com/file.nzb --as-queued
torbox usenet control 42 --operation delete --yes

# Manage web downloads
torbox webdl list
torbox webdl create https://example.com/file.zip
torbox webdl hosters --json          # List supported hosters (no auth needed)

# Manage queued downloads
# (queued items are created with --as-queued on the create endpoints)
torbox queued list
torbox queued control 5 delete --yes

# Manage notifications
torbox notifications list
torbox notifications test
torbox notifications clear --yes

# Stream management (no revocation endpoint exists in the API)
torbox stream create 42 --file-id 1 --type torrent
torbox stream data <token>

# Cloud upload jobs (integrations)
torbox integrations jobs <job-id>
torbox integrations cancel <job-id> --yes
```

### Cron-Safe Automation

```bash
# Auto-retry with backoff so rate limits don't kill nightly jobs
torbox torrents list --auto-retry --json --quiet > /var/log/torbox-backup.json

# Silent JSON output for scheduled tasks
torbox torrents list --json --quiet
```

### Debug a Failing Command

```bash
# Verbose mode shows request timing and headers
torbox general status --verbose

# Inspect why auth isn't resolving where you expect
torbox config doctor
```

### Profiles (Multiple Accounts)

Create an INI-style config at `~/.config/torbox-cli/config.env`:

```ini
[default]
TORBOX_API_KEY = tb-your-default-key

[work]
TORBOX_API_KEY = tb-your-work-key
TORBOX_TIMEOUT = 60
```

Select a profile with `--profile`:

```bash
torbox --profile work torrents list
torbox --profile work --field data torrents list --json
```

Profiles support all config keys: `TORBOX_API_KEY`, `TORBOX_BASE_URL`, `TORBOX_TIMEOUT`, `TORBOX_RETRIES`.

### Live Monitor (`monitor`)

Full-screen htop-style TUI dashboard showing live download activity across all TorBox categories. Polls all 4 list endpoints in parallel and refreshes every second.

```bash
# Start the monitor
torbox monitor

# Custom refresh interval and sort
torbox monitor --interval 2 --sort speed

# Filter by name substring
torbox monitor --filter linux

# Fewer columns for small terminals
torbox monitor --compact
```

#### What You See

```
 TorBox Monitor   Active: 7   DL: 45.2 MB/s   Sort: status   Ctrl-C quit

 Torrents (3)
  ID  Name              Status  Size      Progress   Speed     ETA
  42  Game of Thrones   DL      8.2 GB    ████░ 67%  12.3MB/s  3m42s
  15  Ubuntu 22.04      SD      4.5 GB    █████100%    -        -

 Usenet (2)
  ID  Name              Status  Size      Progress   Speed     ETA
  10  Linux ISO          DL      2.1 GB    ██░░░ 34%   5.1MB/s  5m12s

 Web Downloads (1) / Queued (1)
  ID  Name              Status  Size      Progress   Speed     ETA
 20   file.zip           DL      500 MB    ░░░░░ 12%   2.3MB/s  3m10s
  5   Music Album       WA         -         -          -        -
```

#### Monitor Flags

| Flag | Default | Description |
|------|---------|-------------|
| `-i, --interval` | `1.0` | Refresh interval in seconds |
| `-s, --sort` | `status` | Sort column: status, name, size, speed, progress |
| `-f, --filter` | — | Filter items by name or status substring |
| `-l, --limit` | `20` | Max items per category |
| `--compact` | — | Hide type badge, speed, and ETA columns |
| `--auto-retry` | — | Auto-retry on rate limits |

Press **Ctrl-C** to exit. The terminal is restored cleanly.

---

## Troubleshooting

### Config Doctor

Run `torbox config doctor` to inspect which auth source is active and what the effective values are:

```bash
torbox config doctor          # human-readable output
torbox config doctor --json   # machine-readable output
```

### Exit Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success |
| 1 | General / validation error |
| 2 | Authentication failure |
| 3 | API / server error |
| 4 | Rate limited |
| 5 | Plan restricted |
| 6 | Not found |
| 130 | Interrupted (Ctrl-C) |

---

## Contributing

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Enable git hooks:
   ```bash
   pre-commit install
   ```

3. Add the Pydantic model to `torbox/models.py`.

4. Add the CLI command to `torbox/commands/*.py` with real-world `help=` text.

5. Add tests in `tests/test_<group>.py`.

6. Run the linter and type checker:
   ```bash
   uv run ruff check torbox/ tests/
   uv run mypy --strict torbox/
   ```

7. Run the test suite (coverage threshold: 65%):
   ```bash
   uv run pytest tests/
   ```

---

## See Also

- [DISCLAIMER.md](DISCLAIMER.md) — legal disclaimer and third-party service notices
- [CHANGELOG.md](CHANGELOG.md) — version history and release notes
- [TorBox API Documentation](https://torbox.app/)
- [TorBox Terms of Service](https://torbox.app/terms)

### Install from Source

```bash
pip install git+https://github.com/SwordfishTrumpet/torbox-cli.git
```

---

## License

MIT
