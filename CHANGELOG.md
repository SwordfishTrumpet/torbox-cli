# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`monitor` command** — Full-screen htop-style TUI dashboard showing live download activity across torrents, usenet, webdl, and queued. Uses Rich `Live` with `screen=True`, polls all 4 APIs concurrently via `ThreadPoolExecutor`, computes speed/ETA from progress deltas, and refreshes every 1s. Supports `--interval`, `--sort`, `--filter`, `--limit`, `--compact`.
- **API parity commands** — `webdl requestdl`, `usenet export`, `webdl async-create`, `queued add`, `stream delete`, `user auth-device-poll`, `user auth-device-complete`, `torrents files`. These fill symmetric gaps where one download type had a feature the others lacked, or an API endpoint existed without a CLI command.

### Fixed
- **StremioClient 429 retry exhaustion** — Fixed bug where a 429 rate-limit response on the final retry attempt would raise a generic `RuntimeError` instead of the actual `HTTPStatusError`.
- **DRY violation: `format_size` duplication** — Removed duplicated `format_size` implementation from `search.py`; now imports from `utils.py`.
- **Inline import cleanup** — Moved repeated inline `import sys` and `from rich.table import Table` imports to module level in `client.py`, `stremio.py`, `search.py`, and `torrents.py`.
- **Import ordering** — Fixed ruff I001 violation in `search.py`.
- **Inconsistent `@handle_errors`** — Added missing decorator to all command functions in `torrents.py`, `usenet.py`, `user.py`, `stream.py`, `webdl.py`, and `queued.py` for consistent per-command JSON error output.
- **Inconsistent JSON envelope pattern** — Standardized `print_json_envelope` call ordering in `queued.py`, `integrations.py`, and `stream.py` to match the rest of the codebase.
- **Redundant imports** — Removed unnecessary `builtins` import in `usenet.py` and redundant local `from pathlib import Path` in `torrents.py`.
- **Unused parameter** — Removed dead `_path` parameter from `formatters.py:extract_field`.
- **DRY: `parse_size`** — Extracted size-parsing logic to `utils.parse_size` for reuse; `search.py` wraps it with CLI-specific error handling.
- **Audit Round 3 (2026-05-20):** 8 bugs fixed across monitor, helpers, torrents, and tests. Highlights: renamed silently-skipped test (`keeps_api_progress`), removed dead dry-run code in `_helpers.py`, fixed `_normalize_items` falsy `downloaded=0` bug, `checkcached show` now emits JSON envelope on Cinemeta failures, deduplicated StremioClient config loading, and covered untested confirmation prompts for `stream delete` and `notifications clear`.
- **Audit Round 3 tests:** 18 new tests added — torrents export edge cases, `extract_field` negative index, `format_envelope` edge cases, `print_error_json` direct unit test, `map_http_status` catchall codes, and confirmation prompt denial tests. Coverage maintained at 88%.

### Added
- **`config_cmd` in package exports** — Added to `commands/__init__.py` imports and `__all__` for consistency.
- **`parse_size` utility tests** — Full test coverage for the new `utils.parse_size` function.
- **Search commands (Stremio addon)** — `streams`, `library`, `popular`, `info` subcommands with Cinemeta title resolution, torrent stream filtering, and metadata lookup.
- `guessit` dependency for rich torrent filename parsing (resolution, source, release group, codecs, year).
- Client-side stream filtering: resolution, cached status, size, seeders, quality, source, genre; plus sorting by seeders/size/quality.
- `DISCLAIMER.md` with legal notice, third-party service disclaimers, and privacy/API key policy.
- README improvements: Requirements, Tips & Flags in Practice, Contributing workflow, See Also section, Cinemeta disclaimer.
- 30+ new tests for search error paths, quiet mode, interactive picker, retry logic, and guessit edge cases.
- Test coverage improved from ~83% to ~87%.
- Snapshot-style regression tests for human-mode table and panel output.
- Dependabot configuration for pip and GitHub Actions.
- Packaging verification tests for wheel/sdist `py.typed` inclusion.
- Homebrew formula update helper script.
- Release artifact signing guidance (`docs/RELEASE_SIGNING.md`).

## [1.0.0] - 2026-05-18

### Added
- Full API v1 coverage: torrents, usenet, web downloads, general, user, RSS, queued, stream.
- JSON mode (`--json` / `-j`) with normalized envelope for LLM/agent consumption.
- Field extraction (`--field` / `-f`) with jq-like dot-path support.
- Rich human-mode output: tables, panels, colored errors.
- Authentication hierarchy: CLI flag > env var > `.env` > XDG config > legacy fallback.
- Rate-limit awareness: `--auto-retry` with exponential backoff and `Retry-After` support.
- Typed exception hierarchy with meaningful exit codes.
- Config doctor (`torbox config doctor`) showing resolution order and effective values.
- Dry-run support (`--dry-run`) on control/edit/delete commands.
- Shell completion support for bash, zsh, and fish.
- Man page generation (`torbox docs --man`).
- `python -m torbox` entry point support.
- Pagination on all list commands.
- Search and export for torrents.
- Destructive confirmation prompts with `--yes` override.
- Verbose request diagnostics (`--verbose`) including timing.
- Compact JSON mode (`--compact`).
- PEP 561 compliance (`torbox/py.typed`).
- Comprehensive test suite with pytest, pytest-httpx, and coverage reporting.
- GitHub Actions CI for lint, type check, and test matrix (Python 3.10–3.12).

### Fixed
- Human-mode error standardization with actionable messages.
- Ctrl-C graceful exit with POSIX exit code 130.
- Missing `--field` paths return `null` and exit code 1.
