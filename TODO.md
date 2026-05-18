# TorBox CLI — Development TODO

## Phase 1: Foundation
- [ ] Scaffold project structure (`pyproject.toml`, directories)
- [ ] Set up `ruff`, `mypy`, `pytest` configuration
- [ ] Implement `config.py` — .env / env var / CLI hierarchy
- [ ] Implement `client.py` — httpx base client with auth & retries
- [ ] Implement `exceptions.py` — full exception hierarchy
- [ ] Implement `models.py` — core pydantic models (StandardResponse, User, Torrent)
- [ ] Implement `utils.py` — size formatter, date parser, hash validator

## Phase 2: Core Commands
- [ ] `general` commands (status, stats, changelogs, speedtest) — no auth needed
- [ ] `user me` — GET user data
- [ ] `torrents list` — GET /torrents/mylist
- [ ] `torrents info` — GET /torrents/mylist?id={id}
- [ ] `torrents create` — POST /torrents/createtorrent (magnet + file upload)
- [ ] `torrents control` — POST /torrents/controltorrent
- [ ] `torrents checkcached` — GET /torrents/checkcached
- [ ] `torrents requestdl` — GET /torrents/requestdl

## Phase 3: Extended Commands
- [ ] `usenet` group (list, create, control, requestdl)
- [ ] `webdl` group (list, create, control, edit, hosters)
- [ ] `user` group (settings, searchengines, transactions, transaction-pdf, confirmation, auth-device-start)
- [ ] `rss` group (list, items, create, edit, delete)
- [ ] `queued` group (list, control)
- [ ] `stream` group (create, data)

## Phase 4: Polish & Distribution
- [ ] Implement `--json` mode with `--field` extraction
- [ ] Implement `rich` human formatters (tables, panels)
- [ ] Add comprehensive help strings to all commands
- [ ] Generate man page support (`torbox docs --man`)
- [ ] Write README.md for public GitHub
- [ ] Set up GitHub Actions CI (lint, type-check, test)
- [ ] Publish to PyPI as `torbox-cli`
- [ ] Generate Homebrew formula

## Phase 5: Testing
- [ ] Mock all API endpoints with `pytest-httpx`
- [ ] CLI integration tests with `CliRunner`
- [ ] Test config hierarchy thoroughly
- [ ] Test error code mapping and exit codes
- [ ] Test `--json` output validity

## Security Checklist (Before Going Public)
- [ ] Verify no secrets in git history (`git log --all --full-history -- .env` etc.)
- [ ] Verify TRD.md, TODO.md, AGENTS.md are in `.gitignore` and never committed
- [ ] Remove any hardcoded tokens or test keys from fixtures
- [ ] Run `git-filter-repo` or BFG if history contains sensitive data
