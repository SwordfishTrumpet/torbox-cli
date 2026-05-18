"""Configuration loader with priority hierarchy for API key and settings."""

from __future__ import annotations

import configparser
import os
import stat
import warnings
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

DEFAULT_BASE_URL = "https://api.torbox.app/v1/api"
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
MAX_TIMEOUT = 300
MAX_RETRIES = 10


class ConfigValidationError(ValueError):
    """Raised when a configuration value is invalid."""


def _check_file_permissions(path: Path) -> None:
    """Warn if a config file has overly permissive permissions (not 0600)."""
    try:
        mode = path.stat().st_mode
        if mode & stat.S_IRWXG or mode & stat.S_IRWXO:
            warnings.warn(
                f"Config file {path} has permissions that are too open. "
                f"Consider chmod 600 to restrict access.",
                stacklevel=3,
            )
    except OSError:
        pass


def _validate_timeout(value: int) -> int:
    """Validate timeout is within acceptable bounds."""
    if value <= 0 or value > MAX_TIMEOUT:
        raise ConfigValidationError(
            f"TORBOX_TIMEOUT must be between 1 and {MAX_TIMEOUT} seconds, got {value}"
        )
    return value


def _validate_retries(value: int) -> int:
    """Validate retries is within acceptable bounds."""
    if value < 0 or value > MAX_RETRIES:
        raise ConfigValidationError(
            f"TORBOX_RETRIES must be between 0 and {MAX_RETRIES}, got {value}"
        )
    return value


def _load_ini_profile(path: Path, profile: str) -> dict[str, str]:
    """Load a specific profile section from an INI-style config file.

    Returns a dict of key-value pairs for the profile, or an empty dict
    if the file or profile does not exist.
    """
    if not path.exists():
        return {}
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    if parser.has_section(profile):
        return dict(parser.items(profile))
    return {}


def load_config(
    api_key_override: str | None = None,
    config_path: str | None = None,
    profile: str | None = None,
) -> dict[str, Any]:
    """Load configuration following the hierarchy (highest wins).

    Priority:
    1. CLI flag override (api_key_override)
    2. TORBOX_API_KEY env var
    3. .env in current directory
    4. ~/.config/torbox-cli/config.env
    5. ~/.torbox-cli.env (legacy)
    6. Optional custom --config file (loaded alongside hierarchy)
    7. Profile-specific settings from INI-style config (lowest priority)
    """
    config: dict[str, Any] = {
        "api_key": None,
        "base_url": DEFAULT_BASE_URL,
        "timeout": DEFAULT_TIMEOUT,
        "retries": DEFAULT_RETRIES,
    }

    if api_key_override:
        config["api_key"] = api_key_override
        return config

    # 2. Env var
    env_key = os.getenv("TORBOX_API_KEY")
    if env_key:
        config["api_key"] = env_key

    # Load .env files (lower priority, do not override env var)
    dotenv_paths = [
        Path.cwd() / ".env",
        Path(config_path) if config_path else None,
        Path.home() / ".config" / "torbox-cli" / "config.env",
        Path.home() / ".torbox-cli.env",
    ]
    for dotenv_path in dotenv_paths:
        if dotenv_path and dotenv_path.exists():
            _check_file_permissions(dotenv_path)
            load_dotenv(dotenv_path=dotenv_path, override=False)

    if not config["api_key"]:
        config["api_key"] = os.getenv("TORBOX_API_KEY")

    # Other settings from env after loading dots
    if base := os.getenv("TORBOX_BASE_URL"):
        config["base_url"] = base
    if timeout_str := os.getenv("TORBOX_TIMEOUT"):
        try:
            config["timeout"] = _validate_timeout(int(timeout_str))
        except ConfigValidationError:
            raise
        except ValueError as exc:
            raise ConfigValidationError(
                f"TORBOX_TIMEOUT must be an integer, got {timeout_str!r}"
            ) from exc
    if retries_str := os.getenv("TORBOX_RETRIES"):
        try:
            config["retries"] = _validate_retries(int(retries_str))
        except ConfigValidationError:
            raise
        except ValueError as exc:
            raise ConfigValidationError(
                f"TORBOX_RETRIES must be an integer, got {retries_str!r}"
            ) from exc

    # 7. Profile-specific settings from INI-style config (lowest priority)
    if profile:
        for cfg_path in dotenv_paths:
            if cfg_path and cfg_path.exists():
                profile_values = _load_ini_profile(cfg_path, profile)
                if profile_values:
                    if not config["api_key"] and profile_values.get("torbox_api_key"):
                        config["api_key"] = profile_values["torbox_api_key"]
                    if profile_values.get("torbox_base_url"):
                        config["base_url"] = profile_values["torbox_base_url"]
                    if profile_values.get("torbox_timeout"):
                        try:
                            config["timeout"] = _validate_timeout(
                                int(profile_values["torbox_timeout"])
                            )
                        except ValueError as exc:
                            raise ConfigValidationError(
                                "TORBOX_TIMEOUT must be an integer, got "
                                f"{profile_values['torbox_timeout']!r}"
                            ) from exc
                    if profile_values.get("torbox_retries"):
                        try:
                            config["retries"] = _validate_retries(
                                int(profile_values["torbox_retries"])
                            )
                        except ValueError as exc:
                            raise ConfigValidationError(
                                "TORBOX_RETRIES must be an integer, got "
                                f"{profile_values['torbox_retries']!r}"
                            ) from exc
                    break

    return config
