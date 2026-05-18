# Legal Disclaimer

This project is an **unofficial, third-party, open-source command-line interface** for the TorBox API.

It is **not affiliated with, endorsed by, sponsored by, or connected to TorBox** or its parent/operating entities in any capacity. The name "TorBox" and any associated trademarks are the property of their respective owners.

This tool is provided **"as is"** without warranty of any kind, express or implied. Use of this CLI is at your own risk and subject to the TorBox Terms of Service and API usage policies.

## Privacy & API Keys

This CLI **does not store, log, or transmit your API key** anywhere except to the TorBox API itself.

- Keys are read from your chosen source (`TORBOX_API_KEY` env var, `--api-key` flag, `.env` file, or config file) and sent directly in API request headers.
- No analytics, telemetry, or error reporting services receive your key.
- Persistent storage of credentials is entirely under your control (local env files or config).

### Cinemeta

Title resolution and metadata lookup depend on the **Cinemeta** service (`v3-cinemeta.strem.io`).

- **Availability and results may vary.** Cinemeta is a third-party metadata aggregator independent of both this project and TorBox.
- If Cinemeta is unavailable or returns no matches, use an **IMDB ID directly** (e.g., `tt0133093`) to bypass title resolution.
- Metadata accuracy (ratings, runtime, genres, cast) reflects whatever Cinemeta provides at the time of request.

### Stremio Addon Endpoints

The `search` commands use TorBox's **Stremio addon endpoints**, which are **not part of the official TorBox REST API** and may change or be removed without notice.
