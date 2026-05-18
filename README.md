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

## Quick Start

```bash
export TORBOX_API_KEY=your-key
torbox torrents list
torbox general status --json
```

## Features

- Every TorBox v1 endpoint exposed as a subcommand
- Human-friendly rich tables and panels, plus `--json` / `-j` for scripting and LLM agents
- `--field` extraction for precise JSON queries
- Flexible auth: CLI flag, env var, `.env` file, or XDG config profiles
- Profile support for multiple accounts via INI-style config
- `--auto-retry` with exponential backoff for rate limits
- `--verbose` / `-v` for request diagnostics and timing
- `--dry-run` on mutating commands to preview requests
- `--compact` for single-line JSON output
- Pagination on all list commands (`--offset`, `--limit`)
- Shell completion (bash, zsh, fish)
- Man page generation (`torbox docs --man`)
- Config doctor (`torbox config doctor`) to inspect resolution order

## Command Overview

| Group | Commands |
|-------|----------|
| `general` | status, stats, changelogs, speedtest |
| `torrents` | list, info, create, control, checkcached, requestdl, export, async-create, edit |
| `usenet` | list, create, control, edit, checkcached, requestdl |
| `webdl` | list, create, control, edit, checkcached, hosters |
| `user` | me, transactions, settings, searchengines, auth-device-start |
| `rss` | list, items, create, edit, delete |
| `queued` | list, control |
| `stream` | create, data |
| `notifications` | list, rss, test, clear |
| `integrations` | jobs, cancel |

Run `torbox --help` or `torbox <group> --help` for detailed usage and examples.

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

1. Add the Pydantic model to `torbox/models.py`.
2. Add the CLI command to `torbox/commands/*.py` with real-world `help=` text.
3. Add tests in `tests/test_<group>.py`.
4. Run `uv run ruff check torbox/ tests/` and `uv run mypy --strict torbox/`.
5. Run `uv run pytest tests/` (coverage threshold: 65%).

## License

MIT
