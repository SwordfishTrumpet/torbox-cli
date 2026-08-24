# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.0] - 2026-08-24

### Added
- **Vendors API command group** — `vendors account`, `accounts`, `account-info`, `refresh`, `register`, `register-user`, `remove-user`, `update-account` (closes #23).
- **`integrations oauth` subcommand group** — list, info, register, callback, success, unregister, discord-linked-roles for the `/integration/oauth/*` lifecycle (closes #20).
- **Dropbox upload provider** — `integrations upload dropbox` via POST /integration/dropbox (closes #19).
- **`user delete`** — DELETE /user/deleteme (closes #16).
- **`user subscriptions`** — GET /user/subscriptions (closes #15).
- **`user stats`** — GET /user/stats (closes #14).
- **`user referral-data`** — GET /user/referraldata (closes #13).
- **`general stats-30days`** — GET /stats/30days (closes #12).
- **`torrents exportdata`** — GET /torrents/exportdata (closes #11).
- **`usenet async-create`** — POST /usenet/asynccreateusenetdownload (closes #10).
- **`usenet checkcached --get`** — GET variant of checkcached, previously POST-only (closes #9).
- **`webdl checkcached --batch`** — POST batch cache checks for unlimited hashes (closes #8).

### Fixed
- Removed `stream delete` and `queued add`, which targeted endpoints absent from the live API (HTTP 404) (closes #22, #21).
- Repointed `nntp credentials`/`nntp reset-password` from non-existent `/user/nntp/*` routes to the live `/usenet/provider/account` and `/usenet/provider/account/resetpw` endpoints (closes #18).
- Replaced broken `user auth-device-poll`/`auth-device-complete` with `user auth-device-token` (POST /user/auth/device/token); added `TorBoxClient.public_post()` for auth-less POST endpoints (closes #17).

### Changed
- README documents intentional non-coverage of the deprecated `/torrents/getqueued` routes and the absence of a `queued add` command.

## [1.2.0] - 2026-07-06

### Added
- **NNTP News Server commands** — `nntp credentials` (GET) and `nntp reset-password` (POST) for the TorBox v9 built-in Usenet News Server.
- **Integration cloud-upload commands** — `integrations upload <provider> <file_id>` (googledrive, pixeldrain, onedrive, gofile, 1fichier), `integrations info <job_id>`, and `integrations list-jobs`.
- **`notifications clear-one <id>`** — clear a single notification (POST /notifications/clear/{id}).
- **`user refresh-token`** and **`user add-referral`** commands.
- **`general ping`** — root health check against `https://api.torbox.app/` via `public_get_absolute()` (bypasses the versioned base URL).
- **`torrents torrentinfo`** — dual-mode: GET by hash or POST by `--magnet`.
- **`--airlocked` option** on `torrents edit`, `usenet edit`, and `webdl edit` (v9.0.0 airlock support).
- TODO.md API gap inventory and diagnostics findings.

### Fixed
- **Test isolation** — nine tests were making real, unmocked calls to the live TorBox API (leaking SSL sockets, passing regardless of response). They now mock endpoints via `httpx_mock` or isolate the environment. Added a permanent `tests/conftest.py` network guard that fails any test attempting a non-loopback connection.
- **Connection-pool leak** — `_get_client()` now closes the `httpx.Client` via `ctx.call_on_close`, preventing leaked sockets.
- Removed an unnecessary `# type: ignore` in `_get_field` by narrowing the return type; `mypy --strict` remains clean.

### Changed
- Rate limit for `/torrents/createtorrent` updated to 300/minute per the v9.0.0 spec.
- Synced dependency floors: `pydantic>=2.13.4`, `python-dotenv>=1.2.2`.

## [1.1.0] - 2026-07-06

### Added
- **`monitor` command** — Full-screen htop-style TUI dashboard showing live download activity across torrents, usenet, webdl, and queued. Uses Rich `Live` with `screen=True`, polls all 4 APIs concurrently via `ThreadPoolExecutor`, computes speed/ETA from progress deltas, and refreshes every 1s. Supports `--interval`, `--sort`, `--filter`, `--limit`, `--compact`.
- **API parity commands** — `webdl requestdl`, `usenet export`, `webdl async-create`, `queued add`, `stream delete`, `user auth-device-poll`, `user auth-device-complete`, `torrents files`. These fill symmetric gaps where one download type had a feature the others lacked, or an API endpoint existed without a CLI command.
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

[unreleased]: https://github.com/SwordfishTrumpet/torbox-cli/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/SwordfishTrumpet/torbox-cli/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/SwordfishTrumpet/torbox-cli/releases/tag/v1.0.0
