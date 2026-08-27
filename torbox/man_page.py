"""Generate a troff man page from the Typer command tree.

Replaces the previous 3-line `.TH` stub for `torbox docs --man`. Walks
the registered command/groups of a typer 0.26 app and emits a real man
page with NAME, SYNOPSIS, DESCRIPTION, GLOBAL OPTIONS, COMMANDS (with
per-command options), EXIT STATUS, and SEE ALSO sections.
"""

from __future__ import annotations

import inspect
from typing import Any

import typer
from typer.models import ArgumentInfo, CommandInfo, OptionInfo, TyperInfo

_EXIT_STATUS = [
    ("0", "success"),
    ("1", "general / validation / client error"),
    ("2", "authentication failure"),
    ("3", "API / server / download error"),
    ("4", "rate limited"),
    ("5", "plan restricted"),
    ("6", "not found"),
    ("130", "interrupted (Ctrl-C)"),
]


def _escape(text: str) -> str:
    """Escape troff special characters for literal text."""
    return text.replace("\\", r"\\").replace("-", r"\-").replace("'", r"\(aq")


def _command_name(ci: CommandInfo) -> str:
    """Resolve the command name typer uses for a CommandInfo."""
    if ci.name:
        return ci.name
    if ci.callback is not None:
        return ci.callback.__name__.replace("_", "-")
    return ""


def _param_lines(callback: Any) -> list[str]:
    """Emit troff .TP blocks for a command callback's typer params.

    The typer Context parameter is skipped; OptionInfo/ArgumentInfo
    defaults carry the declaration strings, requiredness, and help text.
    """
    lines: list[str] = []
    for _name, param in inspect.signature(callback).parameters.items():
        default = param.default
        if not isinstance(default, (OptionInfo, ArgumentInfo)):
            continue
        decls = " ".join(default.param_decls) if default.param_decls else _name
        lines.append(".TP")
        lines.append(f".B {_escape(decls)}")
        if default.help:
            lines.append(_escape(default.help))
    return lines


def _render_command(ci: CommandInfo) -> list[str]:
    lines = [".TP", f".B {_escape(_command_name(ci))}"]
    if ci.help:
        lines.append(_escape(ci.help))
    lines.extend(_param_lines(ci.callback))
    return lines


def _render_group(group: TyperInfo) -> list[str]:
    """Render a top-level group section, recursing into sub-groups."""
    lines = [".SS " + _escape(group.name or "")]
    if group.help:
        lines.append(_escape(group.help))
    typer_instance = group.typer_instance
    if typer_instance is None:
        return lines
    for cmd in typer_instance.registered_commands:
        if cmd.hidden:
            continue
        lines.extend(_render_command(cmd))
    for sub in typer_instance.registered_groups:
        lines.extend(_render_group(sub))
    return lines


def generate_man_page(app: typer.Typer) -> str:
    """Generate a troff man page for the given Typer app."""
    lines: list[str] = []
    lines.append(".TH TORBOX 1")
    lines.append(".SH NAME")
    lines.append(r"torbox \- TorBox CLI")
    lines.append(".SH SYNOPSIS")
    lines.append(r".B torbox")
    lines.append(r"[\fIOPTIONS\fR] \fICOMMAND\fR [\fIARGS\fR]...")
    lines.append(".SH DESCRIPTION")
    lines.append(_escape(app.info.help or "TorBox CLI."))
    lines.append(".SH GLOBAL OPTIONS")
    if app.registered_callback and app.registered_callback.callback:
        lines.extend(_param_lines(app.registered_callback.callback))
    lines.append(".SH COMMANDS")
    for group in app.registered_groups:
        lines.extend(_render_group(group))
    for cmd in app.registered_commands:
        if cmd.hidden:
            continue
        lines.extend(_render_command(cmd))
    lines.append(".SH EXIT STATUS")
    for code, meaning in _EXIT_STATUS:
        lines.append(".TP")
        lines.append(f".B {code}")
        lines.append(meaning)
    lines.append(".SH SEE ALSO")
    lines.append(r".BR https://api.torbox.app/docs ,")
    lines.append(r".BR https://github.com/SwordfishTrumpet/torbox-cli")
    return "\n".join(lines) + "\n"
