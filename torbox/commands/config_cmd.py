"""Config commands: doctor, inspect config resolution."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import typer
from typer import Context

from torbox.commands._helpers import (
    handle_errors,
    print_json_envelope,
)
from torbox.config import load_config
from torbox.formatters import print_dict_panel

app = typer.Typer(help="Configuration inspection and diagnostics")


def _resolve_config_sources(config_path: str | None = None) -> list[dict[str, Any]]:
    """Inspect the config resolution order and report what was found."""
    sources: list[dict[str, Any]] = []

    # 1. CLI override
    sources.append(
        {
            "source": "CLI --api-key",
            "present": False,
            "value": None,
        }
    )

    # 2. Env var
    env_key = os.getenv("TORBOX_API_KEY")
    sources.append(
        {
            "source": "TORBOX_API_KEY env var",
            "present": bool(env_key),
            "value": "***" if env_key else None,
        }
    )

    # 3. .env in cwd
    cwd_dotenv = Path.cwd() / ".env"
    sources.append(
        {
            "source": f".env in CWD ({cwd_dotenv})",
            "present": cwd_dotenv.exists(),
            "value": None,
        }
    )

    # 4. Custom config file
    if config_path:
        custom = Path(config_path)
        sources.append(
            {
                "source": f"Custom --config ({custom})",
                "present": custom.exists(),
                "value": None,
            }
        )

    # 5. XDG config
    xdg = Path.home() / ".config" / "torbox-cli" / "config.env"
    sources.append(
        {
            "source": f"XDG config ({xdg})",
            "present": xdg.exists(),
            "value": None,
        }
    )

    # 6. Legacy fallback
    legacy = Path.home() / ".torbox-cli.env"
    sources.append(
        {
            "source": f"Legacy config ({legacy})",
            "present": legacy.exists(),
            "value": None,
        }
    )

    return sources


@app.command(
    help=(
        "Inspect config resolution order and effective values. "
        "Example: torbox config doctor --json"
    )
)
@handle_errors
def doctor(
    ctx: Context,
    json: bool = typer.Option(False, "--json", "-j", help="Raw JSON output"),
) -> None:
    """Show how configuration is resolved and what the effective values are."""
    config_path = ctx.obj.get("config") if ctx.obj else None
    profile = ctx.obj.get("profile") if ctx.obj else None
    cfg = load_config(config_path=config_path, profile=profile)
    sources = _resolve_config_sources(config_path)

    # Mark CLI override if present
    api_key_override = ctx.obj.get("api_key") if ctx.obj else None
    if api_key_override:
        sources[0]["present"] = True
        sources[0]["value"] = "***"

    effective = {
        "api_key": "***" if cfg["api_key"] else None,
        "base_url": cfg["base_url"],
        "timeout": cfg["timeout"],
        "retries": cfg["retries"],
        "profile": profile,
    }

    data = {
        "success": True,
        "sources": sources,
        "effective": effective,
    }

    print_json_envelope(ctx, data, "config doctor", local_json=json)
    if (ctx.obj and ctx.obj.get("json")) or json:
        return
    print("Config Resolution Order:\n")
    for src in sources:
        status = "✓" if src["present"] else "✗"
        print(f"  [{status}] {src['source']}")
    if profile:
        print(f"\nActive Profile: {profile}")
    print("\nEffective Values:")
    print_dict_panel(effective, "Effective Config")
