# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
