# TorBox CLI — Technical Requirements Document (TRD)

**Version:** 1.0  
**Date:** 2025-08-24  
**Status:** Draft  
**Classification:** Local-only — DO NOT PUSH TO PUBLIC REPOSITORY

---

## 1. Executive Summary

Build a full-featured, LLM-first CLI wrapper for the TorBox API v1 (`https://api.torbox.app/v1`). The tool must expose every public endpoint as an intuitive, well-documented subcommand, support both human-readable and machine-parseable (JSON) output, and handle authentication flexibly via `.env` files, environment variables, or CLI flags.

The CLI is designed primarily for **LLM agent consumption** (via `--json` output) while remaining fully usable by humans (via `rich`-formatted tables and progress indicators).

---

## 2. Goals & Non-Goals

### Goals
- [ ] 100% API coverage of TorBox v1 public endpoints
- [ ] LLM-first JSON output mode (`--json`) with field extraction (`--field`)
- [ ] Zero-configuration authentication via `.env` / env vars / CLI flags
- [ ] Comprehensive self-documenting help at every level (`-h`, `--help`, man pages)
- [ ] Meaningful exit codes (0=success, 1=general error, 2=auth error, 3=API error)
- [ ] Robust error handling with typed exceptions mapping TorBox error codes
- [ ] Rate-limit awareness with proactive backoff suggestions
- [ ] PyPI distribution as `torbox-cli`
- [ ] Python 3.10+ compatibility

### Non-Goals
- Interactive TUI mode (out of scope; keep it simple)
- Real-time streaming progress bars (not required for LLM use)
- GUI wrapper
- Windows-specific installer (pip install is sufficient)

---

## 3. Technology Stack

| Layer | Tool | Rationale |
|-------|------|-----------|
| Language | Python 3.10+ | Widest ecosystem, LLM-native, type hints |
| CLI Framework | **Typer** (on Click) | Community standard, auto-generates help, type-hint driven |
| HTTP Client | **httpx** | Modern, async-capable, timeout handling, retries |
| Data Validation | **pydantic** v2 | Models all API request/response schemas |
| Output (Human) | **rich** | Beautiful tables, progress, colors |
| Output (JSON) | `json` stdlib + pydantic | Pretty-printed, valid JSON |
| Environment | **python-dotenv** | `.env` file loading |
| Config Dir | XDG Base Dir spec | `~/.config/torbox-cli/` |
| Lint/Format | **ruff** | Fast, unified linter & formatter |
| Type Check | **mypy --strict** | Strict typing discipline |
| Testing | **pytest** + **pytest-httpx** | HTTP mocking, CLI integration via `typer.testing.CliRunner` |
| Build | **hatchling** (via `pyproject.toml`) | Modern build backend |

---

## 4. Architecture

```
torbox/
├── __init__.py           # Package metadata (__version__)
├── cli.py                # Main Typer app, global flags, command registration
├── client.py             # HTTP client: base URL, auth, retries, rate-limit tracking
├── config.py             # Config loader with hierarchy: CLI > env > .env > config file
├── models.py             # Pydantic models for ALL API request/response schemas
├── formatters.py         # Human (rich tables) + JSON output formatters
├── exceptions.py         # Custom exception hierarchy mapping TorBox error codes
├── utils.py              # Helpers: size formatting, date parsing, hash validation
├── commands/
│   ├── __init__.py
│   ├── torrents.py       # torrents list|info|create|control|checkcached|requestdl|export|search
│   ├── usenet.py         # usenet list|create|control|requestdl
│   ├── webdl.py          # webdl list|create|control|edit|hosters
│   ├── general.py        # general status|stats|changelogs|speedtest
│   ├── user.py           # user me|settings|searchengines|transactions|transaction-pdf|confirmation|auth-device-start
│   ├── rss.py            # rss list|items|create|edit|delete
│   ├── queued.py         # queued list|control
│   └── stream.py         # stream create|data
└── docs/
    └── man/              # Generated man page sources (troff)
```

---

## 5. Command Structure

Top-level app: `torbox`

### Global Flags (available on every command)

| Flag | Short | Type | Description |
|------|-------|------|-------------|
| `--api-key` | `-k` | `str` | Override API key |
| `--json` | `-j` | `bool` | Emit raw JSON (LLM mode) |
| `--field` | `-f` | `str` | Extract dot-path from JSON (e.g. `data.0.name`) |
| `--config` | | `Path` | Path to custom config file |
| `--quiet` | `-q` | `bool` | Suppress non-essential output |
| `--verbose` | `-v` | `bool` | Debug logging to stderr |
| `--version` | | `bool` | Show version and exit |

### Command Groups

#### 5.1 `torbox torrents ...`

| Command | API Endpoint | Args / Options |
|---------|-------------|----------------|
| `list` | `GET /torrents/mylist` | `--offset`, `--limit`, `--status` |
| `info <id>` | `GET /torrents/mylist?id={id}` | positional `id` |
| `create <magnet\|file>` | `POST /torrents/createtorrent` | positional `source`; `--name`, `--seed` |
| `control <id>` | `POST /torrents/controltorrent` | positional `id`; `--operation delete\|pause\|resume`, `--all` |
| `checkcached <hash>...` | `GET /torrents/checkcached` | positional varargs `hash` |
| `requestdl <id>` | `GET /torrents/requestdl` | positional `id`; `--file-id`, `--zip-link`, `--redirect`, `--append-name` |
| `export <id>` | export .torrent | positional `id` |
| `search <query>` | search API | positional `query` |

#### 5.2 `torbox usenet ...`

| Command | API Endpoint | Args / Options |
|---------|-------------|----------------|
| `list` | list downloads | `--offset`, `--limit` |
| `create <nzb>` | `POST /usenet/createusenetdownload` | positional `nzb` (file or URL); `--name`, `--password` |
| `control <id>` | `POST /usenet/controlusenetdownload` | positional `id`; `--operation delete\|pause\|resume`, `--all` |
| `requestdl <id>` | `GET /usenet/requestdl` | positional `id`; `--file-id`, `--zip-link`, `--redirect` |

#### 5.3 `torbox webdl ...`

| Command | API Endpoint | Args / Options |
|---------|-------------|----------------|
| `list` | list downloads | `--offset`, `--limit` |
| `create <link>` | `POST /webdl/createwebdownload` | positional `link`; `--password`, `--name`, `--as-queued`, `--add-only-if-cached` |
| `control <id>` | `POST /webdl/controlwebdownload` | positional `id`; `--operation delete\|pause\|resume`, `--all` |
| `edit <id>` | `PUT /webdl/editwebdownload` | positional `id`; `--name`, `--tags`, `--alternative-hashes` |
| `hosters` | `GET /webdl/hosters` | none (optional auth for live user data) |

#### 5.4 `torbox general ...`

| Command | API Endpoint | Auth |
|---------|-------------|------|
| `status` | `GET /` | None |
| `stats` | `GET /stats` | None |
| `changelogs` | `GET /changelogs/json` | None |
| `speedtest` | `GET /speedtest` | None |

#### 5.5 `torbox user ...`

| Command | API Endpoint | Notes |
|---------|-------------|-------|
| `me` | `GET /user` | Include `--settings` flag |
| `settings` | `PUT /user/settings/editsettings` | Interactive or JSON blob |
| `searchengines` | `GET /user/settings/searchengines` | `--id` for specific engine |
| `transactions` | `GET /user/transactions` | `--offset`, `--limit` |
| `transaction-pdf <id>` | `GET /user/transaction/pdf` | Download PDF to stdout or file |
| `confirmation` | `GET /user/getconfirmation` | Request 6-digit code |
| `auth-device-start` | `GET /user/auth/device/start` | `--app` name parameter |

#### 5.6 `torbox rss ...`

| Command | API Endpoint |
|---------|-------------|
| `list` | `GET /rss/getfeeds` |
| `items <feed-id>` | `GET /rss/getfeeditems` |
| `create` | management |
| `edit <id>` | management |
| `delete <id>` | management |

#### 5.7 `torbox queued ...`

| Command | API Endpoint |
|---------|-------------|
| `list` | `GET /queued/getqueued` |
| `control` | `POST /queued/controlqueued` |

#### 5.8 `torbox stream ...`

| Command | API Endpoint | Args / Options |
|---------|-------------|----------------|
| `create <id>` | `GET /stream/createstream` | `--type torrent\|usenet\|webdownload`, `--file-id`, `--chosen-subtitle-index`, `--chosen-audio-index`, `--chosen-resolution-index` |
| `data <token>` | `GET /stream/getstreamdata` | `--chosen-subtitle-index`, `--chosen-audio-index`, `--chosen-resolution-index` |

#### 5.9 `torbox docs --man`

Generate and output a man page for the CLI. Delegates to `help2man` if available, otherwise emits troff to stdout.

---

## 6. Configuration & Authentication

### Hierarchy (highest priority wins)

1. CLI flag: `--api-key KEY`
2. Environment variable: `TORBOX_API_KEY`
3. `.env` file in current working directory
4. `~/.config/torbox-cli/config.env`
5. `~/.torbox-cli.env` (legacy fallback)

### Config File Format (`config.env`)

```bash
TORBOX_API_KEY=tb-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
TORBOX_BASE_URL=https://api.torbox.app/v1
TORBOX_TIMEOUT=30
TORBOX_RETRIES=3
```

### Implementation Details
- Use `python-dotenv` to load `.env` files
- Support `--config <path>` to override default config file location
- All API key values are treated as opaque strings; no validation except non-empty
- Warn if no API key is found before executing authenticated commands

---

## 7. Output Formatting

### 7.1 Human Mode (default)

Use `rich` for:
- **Tables:** `torrents list`, `usenet list`, `webdl list`, `hosters`, `rss list`
- **Panels:** single-item info (`torrents info`, `user me`)
- **Progress:** long-running operations (file uploads)
- **Colors:** success=green, error=red, warning=yellow
- **Pretty JSON:** optionally via `--json --pretty` (for human-readable JSON)

### 7.2 JSON Mode (`--json` / `-j`)

When `--json` is passed:
- Skip all `rich` formatting
- Output **only** valid JSON to stdout
- Structure:
  ```json
  {
    "success": true,
    "command": "torrents list",
    "data": { ... },
    "meta": {
      "timestamp": "2025-08-24T15:18:28Z",
      "request_duration_ms": 245
    }
  }
  ```
- If the API returns an error, still output valid JSON with `success: false`
- Exit code 0 only if both HTTP and API-level success are true

### 7.3 Field Extraction (`--field` / `-f`)

Works only with `--json`. Supports dot notation:

```bash
# Extract just the names of the first 5 torrents
torbox torrents list --json --field "data.0.name"

# Extract all data array
torbox torrents list --json --field "data"
```

If the field does not exist, output `null` and exit code 1.

---

## 8. Error Handling & Exit Codes

### Exception Hierarchy

```
TorBoxError (base)
├── AuthenticationError     # 403, NO_AUTH, BAD_TOKEN, AUTH_ERROR
├── ValidationError         # 400, INVALID_OPTION, MISSING_REQUIRED_OPTION
├── NotFoundError           # 404, ITEM_NOT_FOUND, ENDPOINT_NOT_FOUND
├── RateLimitError          # 429
├── PlanRestrictedError     # PLAN_RESTRICTED_FEATURE
├── DownloadError           # DOWNLOAD_SERVER_ERROR, COOLDOWN_LIMIT, ACTIVE_LIMIT
├── ServerError             # 500, DATABASE_ERROR, UNKNOWN_ERROR
└── ClientError             # catch-all for client-caused errors
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (CLI usage, unexpected exception) |
| 2 | Authentication error |
| 3 | API error (TorBox returned `success: false`) |
| 4 | Rate limited (429) |
| 5 | Plan restricted feature |
| 6 | Item not found |
| 130 | Interrupted (Ctrl-C) |

### Error Output

**Human mode:**
```
❌ Authentication failed: BAD_TOKEN
   The provided token is invalid. Check your TORBOX_API_KEY.
```

**JSON mode:**
```json
{
  "success": false,
  "error": "BAD_TOKEN",
  "detail": "The provided token is invalid.",
  "exit_code": 2
}
```

---

## 9. Rate Limiting

### Awareness

The client must:
1. Track 429 responses and read `Retry-After` header
2. Suggest backoff in human mode
3. Automatically retry once on 429 (with exponential backoff) if `--auto-retry` is enabled
4. Track per-endpoint limits:
   - Default: 300 req/min per token
   - `POST /torrents/createtorrent`: 60/hour
   - `POST /usenet/createusenetdownload`: 60/hour
   - `POST /webdl/createwebdownload`: 60/hour

### Implementation
- Use `httpx` with `httpx.Limits(max_connections=20)`
- Optional: maintain a simple in-memory token bucket tracker (not enforced, advisory only)
- Print warning to stderr when approaching limits in verbose mode

---

## 10. Pydantic Models

### Standard Response Model

```python
class TorBoxResponse(BaseModel):
    success: bool
    error: str | None
    detail: str
    data: Any
```

### API-Specific Models

Create typed models for every endpoint's `data` field:

- `Torrent` / `TorrentList` — for `torrents/mylist`
- `UsenetDownload` / `UsenetDownloadList`
- `WebDownload` / `WebDownloadList`
- `Hoster` / `HosterList`
- `User` / `UserSettings`
- `SearchEngine` / `SearchEngineList`
- `Transaction` / `TransactionList`
- `RSSFeed` / `RSSFeedItem`
- `QueuedDownload`
- `StreamData` / `StreamMetadata`
- `DeviceCodeAuth`

All models must:
- Use `from __future__ import annotations`
- Have `model_config = ConfigDict(from_attributes=True)` where needed
- Support `.model_dump_json()` for CLI JSON output

---

## 11. Testing Strategy

### Unit Tests
- Pydantic model validation with edge cases
- Config loader hierarchy verification
- Field extraction (`--field`) logic
- Error code mapping

### Integration Tests (with `pytest-httpx`)
- Mock every API endpoint
- Test CLI commands via `typer.testing.CliRunner`
- Verify `--json` output is parseable
- Verify exit codes match spec

### Fixtures
Store mock API responses in `tests/fixtures/` as JSON files.

### CI/CD
- GitHub Actions running `ruff check`, `ruff format --check`, `mypy --strict`, `pytest`
- Test matrix: Python 3.10, 3.11, 3.12

---

## 12. Distribution

### PyPI
- Package name: `torbox-cli`
- Entry point: `torbox = torbox.cli:app`
- `pyproject.toml` with `hatchling` build backend
- Automated publishing via GitHub Actions on release tag

### Homebrew
- Generate formula with `homebrew-pypi-poet` or manually
- Formula name: `torbox-cli`

### pipx
- Primary installation method for end users:
  ```bash
  pipx install torbox-cli
  ```

---

## 13. Documentation

### In-App Help
Every command must have detailed `help=` strings:
- Top-level: `torbox --help` → overview of all groups
- Group: `torbox torrents --help` → overview of torrent commands
- Command: `torbox torrents create --help` → full argument descriptions, examples

### Man Page
- `torbox docs --man` generates troff output
- If `help2man` is installed, delegate for better formatting
- Pipe to `man -l /dev/stdin` for immediate viewing

### README (public)
The public README (for GitHub) will contain:
- Installation instructions
- Quick start
- Command overview
- `--json` mode guide for LLM integrators
- Authentication setup
- Contributing guidelines

### Local-Only Files
These files are tracked in local git but MUST NEVER be pushed to GitHub:
- `TRD.md` (this document)
- `TODO.md`
- `AGENTS.md`

---

## 14. Security & Privacy

### API Key Handling
- API keys are never logged (redacted in `--verbose` output)
- API keys are never printed in error messages
- Config files must have `chmod 600` enforced
- `.env` files are in `.gitignore` by default

### Public Repository Safety
- Before making the repository public, scrub git history for any secrets
- Verify no local-only files were ever committed
- Use `git-filter-repo` or BFG if history cleanup is needed

---

## 15. Success Criteria Checklist

- [ ] Every TorBox API v1 endpoint has a corresponding CLI command
- [ ] `--help` is comprehensive and accurate at every level
- [ ] `--json` output is valid JSON suitable for LLM parsing
- [ ] Authentication works via `.env`, env var, or CLI flag seamlessly
- [ ] Exit codes are meaningful and documented
- [ ] No secrets or local planning files leak to the public repository
- [ ] `ruff check` passes with zero warnings
- [ ] `mypy --strict` passes with zero errors
- [ ] `pytest` passes with 100% API endpoint coverage mocked
- [ ] Package installs cleanly via `pipx install torbox-cli`

---

## 16. Open Questions

1. Should we support async operations for batch commands (e.g., checkcached with 100 hashes)?
2. Do we want a shell completion generator (`torbox --install-completion`)?
3. Should we cache hoster lists locally to avoid repeated API calls?
4. What's the preferred format for `torrents export` — stdout raw bytes or save to file?

---

## Appendix A: TorBox Error Code Mapping

| Error Code | Exception Class | Exit Code |
|------------|-----------------|-----------|
| `DATABASE_ERROR` | `ServerError` | 3 |
| `UNKNOWN_ERROR` | `ServerError` | 3 |
| `NO_AUTH` | `AuthenticationError` | 2 |
| `BAD_TOKEN` | `AuthenticationError` | 2 |
| `AUTH_ERROR` | `AuthenticationError` | 2 |
| `INVALID_OPTION` | `ValidationError` | 1 |
| `REDIRECT_ERROR` | `ServerError` | 3 |
| `OAUTH_VERIFICATION_ERROR` | `AuthenticationError` | 2 |
| `ENDPOINT_NOT_FOUND` | `NotFoundError` | 6 |
| `ITEM_NOT_FOUND` | `NotFoundError` | 6 |
| `PLAN_RESTRICTED_FEATURE` | `PlanRestrictedError` | 5 |
| `DUPLICATE_ITEM` | `ValidationError` | 1 |
| `BOZO_RSS_FEED` | `ValidationError` | 1 |
| `TOO_MUCH_DATA` | `ValidationError` | 1 |
| `DOWNLOAD_TOO_LARGE` | `ValidationError` | 1 |
| `MISSING_REQUIRED_OPTION` | `ValidationError` | 1 |
| `TOO_MANY_OPTIONS` | `ValidationError` | 1 |
| `BOZO_TORRENT` | `ValidationError` | 1 |
| `NO_SERVERS_AVAILABLE_ERROR` | `ServerError` | 3 |
| `MONTHLY_LIMIT` | `PlanRestrictedError` | 5 |
| `COOLDOWN_LIMIT` | `DownloadError` | 3 |
| `ACTIVE_LIMIT` | `DownloadError` | 3 |
| `DOWNLOAD_SERVER_ERROR` | `DownloadError` | 3 |
| `BOZO_NZB` | `ValidationError` | 1 |
| `SEARCH_ERROR` | `ServerError` | 3 |
| `INVALID_DEVICE` | `AuthenticationError` | 2 |
| `DIFF_ISSUE` | `ValidationError` | 1 |
| `LINK_OFFLINE` | `ValidationError` | 1 |
| `VENDOR_DISABLED` | `ValidationError` | 1 |
| `BOZO_REGEX` | `ValidationError` | 1 |
| `BAD_CONFIRMATION` | `ValidationError` | 1 |
| `CONFIRMATION_EXPIRED` | `ValidationError` | 1 |
| `BOZO_FILE` | `ValidationError` | 1 |

---

## Appendix B: Real-Debrid API Translation

For integrators migrating from Real-Debrid:

| Real-Debrid | TorBox CLI |
|-------------|------------|
| `GET /torrents` | `torbox torrents list` |
| `GET /torrents/info/{id}` | `torbox torrents info <id>` |
| `GET /torrents/instantAvailability/{hash}` | `torbox torrents checkcached <hash>` |
| `PUT /torrents/addTorrent` / `POST /torrents/addMagnet` | `torbox torrents create <magnet\|file>` |
| `DELETE /torrents/delete/{id}` | `torbox torrents control <id> --operation delete` |
| `POST /unrestrict/link` | `torbox torrents requestdl <id> --file-id <n>` |
