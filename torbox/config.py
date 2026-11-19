"""Configuration loader with priority hierarchy for API key and settings."""

from __future__ import annotations

import configparser
import os
import re
import stat
import warnings
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from torbox.exceptions import TorBoxError

DEFAULT_BASE_URL = "https://api.torbox.app/v1/api"
DEFAULT_SERVER_URL = "https://api.torbox.app"
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
MAX_TIMEOUT = 300
MAX_RETRIES = 10


class ConfigValidationError(TorBoxError):
    """Raised when a configuration value is invalid.

    Subclasses ``TorBoxError`` (exit code 1) so configuration failures
    flow through the typed error boundary (``handle_errors`` /
    ``cli_entry``) instead of escaping as raw tracebacks.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=1)


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


_INI_SECTION_RE = re.compile(r"^\s*\[[^\]]+\]\s*$")


def _is_ini_file(path: Path) -> bool:
    """Return True when the file carries INI section headers.

    Such a file holds *profiles*, not flat key=value settings, and must not
    be read with ``dotenv_values``: python-dotenv ignores section headers and
    keeps only the last duplicate key in the file, so every section's
    ``TORBOX_API_KEY`` collapses onto the final section's value (#63).
    """
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                stripped = line.lstrip()
                if stripped.startswith(("#", ";")):
                    continue
                if _INI_SECTION_RE.match(line):
                    return True
    except OSError:
        return False
    return False


def _load_ini_profile(path: Path, profile: str) -> dict[str, str]:
    """Load a specific profile section from an INI-style config file.

    Returns a dict of key-value pairs for the profile, or an empty dict if the
    file or the profile does not exist.

    Keys written before the first section header are read as ``[default]``,
    which is how configparser treats them once the header is supplied: a file
    that mixes flat keys with profiles keeps its flat keys instead of losing
    them silently (#63).
    """
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    if _has_preamble_keys(text):
        text = "[default]\n" + text
    parser = configparser.ConfigParser()
    try:
        parser.read_string(text, source=str(path))
    except configparser.Error:
        # A malformed section layout is not a usable profile source.
        return {}
    if parser.has_section(profile):
        return dict(parser.items(profile))
    return {}


def _has_preamble_keys(text: str) -> bool:
    """Return True when key=value lines precede the first section header."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            continue
        return not _INI_SECTION_RE.match(line)
    return False


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
    7. Profile-specific settings from INI-style config (lowest priority).
       A file with section headers supplies only the selected section, or
       ``[default]`` when no ``--profile`` is given; its other sections are
       never read.
    """
    config: dict[str, Any] = {
        "api_key": None,
        "base_url": DEFAULT_BASE_URL,
        "timeout": DEFAULT_TIMEOUT,
        "retries": DEFAULT_RETRIES,
    }

    if config_path and not Path(config_path).exists():
        raise ConfigValidationError(f"Config file not found: {config_path}")

    if api_key_override:
        # Highest-priority key value only: the override must not suppress the
        # base url, timeout, retries, config file, or profile resolution below.
        config["api_key"] = api_key_override

    # 2. Env var (unless the CLI flag already won)
    env_key = os.getenv("TORBOX_API_KEY")
    if env_key and not config["api_key"]:
        config["api_key"] = env_key

    # Load .env files (lower priority, do not override env var).
    # Use dotenv_values() instead of load_dotenv() to avoid polluting
    # os.environ, which breaks tests that rely on clean environments.
    dotenv_paths = [
        Path.cwd() / ".env",
        Path(config_path) if config_path else None,
        Path.home() / ".config" / "torbox-cli" / "config.env",
        Path.home() / ".torbox-cli.env",
    ]
    dotenv_merged: dict[str, str | None] = {}
    for dotenv_path in dotenv_paths:
        if dotenv_path and dotenv_path.exists():
            _check_file_permissions(dotenv_path)
            # A profile INI file is not a .env file: it contributes only the
            # selected section below, so other sections can never decide the
            # key or base url (#63).
            if _is_ini_file(dotenv_path):
                continue
            values = dotenv_values(dotenv_path)
            # Merge with lower priority — don't override already-seen keys
            for k, v in values.items():
                if k not in dotenv_merged:
                    dotenv_merged[k] = v

    # Apply dotenv values for any key not already set by env var
    if not config["api_key"]:
        config["api_key"] = dotenv_merged.get("TORBOX_API_KEY")

    # Which settings a higher-priority source already decided. A profile is the
    # lowest-priority source, so it fills only what is still unset (#70).
    resolved_above_profile: set[str] = set()

    # Other settings: env var wins, then dotenv, then default
    if base := (os.getenv("TORBOX_BASE_URL") or dotenv_merged.get("TORBOX_BASE_URL")):
        config["base_url"] = base
        resolved_above_profile.add("base_url")
    if timeout_str := (
        os.getenv("TORBOX_TIMEOUT") or dotenv_merged.get("TORBOX_TIMEOUT")
    ):
        try:
            config["timeout"] = _validate_timeout(int(timeout_str))
        except ConfigValidationError:
            raise
        except ValueError as exc:
            raise ConfigValidationError(
                f"TORBOX_TIMEOUT must be an integer, got {timeout_str!r}"
            ) from exc
        resolved_above_profile.add("timeout")
    if retries_str := (
        os.getenv("TORBOX_RETRIES") or dotenv_merged.get("TORBOX_RETRIES")
    ):
        try:
            config["retries"] = _validate_retries(int(retries_str))
        except ConfigValidationError:
            raise
        except ValueError as exc:
            raise ConfigValidationError(
                f"TORBOX_RETRIES must be an integer, got {retries_str!r}"
            ) from exc
        resolved_above_profile.add("retries")

    # 7. Profile-specific settings from INI-style config (lowest priority).
    # Without --profile the documented [default] section applies, so a file
    # that defines profiles still supplies one of them (#63).
    section = profile or "default"
    for cfg_path in dotenv_paths:
        if not cfg_path or not cfg_path.exists():
            continue
        profile_values = _load_ini_profile(cfg_path, section)
        if not profile_values:
            continue
        if not config["api_key"] and profile_values.get("torbox_api_key"):
            config["api_key"] = profile_values["torbox_api_key"]
        if "base_url" not in resolved_above_profile and profile_values.get(
            "torbox_base_url"
        ):
            config["base_url"] = profile_values["torbox_base_url"]
        if "timeout" not in resolved_above_profile and profile_values.get(
            "torbox_timeout"
        ):
            try:
                config["timeout"] = _validate_timeout(
                    int(profile_values["torbox_timeout"])
                )
            except ValueError as exc:
                raise ConfigValidationError(
                    "TORBOX_TIMEOUT must be an integer, got "
                    f"{profile_values['torbox_timeout']!r}"
                ) from exc
        if "retries" not in resolved_above_profile and profile_values.get(
            "torbox_retries"
        ):
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
