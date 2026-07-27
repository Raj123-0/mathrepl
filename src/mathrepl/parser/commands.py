"""Command dispatcher — handles colon-prefixed meta-commands.

Commands are processed by the TUI layer; this module provides the registry,
help text, and parsing for each command.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CommandSpec:
    """Specification for a single colon-command."""

    name: str
    aliases: list[str]
    description: str
    usage: str
    min_args: int = 0
    max_args: int | None = None  # None = unlimited


# ---------------------------------------------------------------------------
# Command registry
# ---------------------------------------------------------------------------

COMMANDS: dict[str, CommandSpec] = {}


def _register(spec: CommandSpec) -> None:
    COMMANDS[spec.name] = spec
    for alias in spec.aliases:
        COMMANDS[alias] = spec


_register(CommandSpec(
    name="help",
    aliases=["h", "?"],
    description="Show this help message or help for a specific command",
    usage=":help [command]",
    max_args=1,
))

_register(CommandSpec(
    name="precision",
    aliases=["prec"],
    description="Set or display the working precision (decimal digits)",
    usage=":precision [N]",
    max_args=1,
))

_register(CommandSpec(
    name="undo",
    aliases=["u"],
    description="Roll back the last state change",
    usage=":undo",
    max_args=0,
))

_register(CommandSpec(
    name="history",
    aliases=["hist"],
    description="Show numbered input history",
    usage=":history [N]",
    max_args=1,
))

_register(CommandSpec(
    name="vars",
    aliases=["v", "variables"],
    description="List all defined variables and their values",
    usage=":vars",
    max_args=0,
))

_register(CommandSpec(
    name="funcs",
    aliases=["functions"],
    description="List all user-defined functions",
    usage=":funcs",
    max_args=0,
))

_register(CommandSpec(
    name="clear",
    aliases=["reset"],
    description="Reset all session state (variables, functions, history)",
    usage=":clear",
    max_args=0,
))

_register(CommandSpec(
    name="save",
    aliases=["s"],
    description="Save the current session to a file",
    usage=":save [filepath]",
    max_args=1,
))

_register(CommandSpec(
    name="load",
    aliases=["l"],
    description="Load a session from a file",
    usage=":load <filepath>",
    min_args=1,
    max_args=1,
))

_register(CommandSpec(
    name="export",
    aliases=["ex"],
    description="Export session to LaTeX or Jupyter notebook",
    usage=":export <latex|jupyter> [filepath]",
    min_args=1,
    max_args=2,
))

_register(CommandSpec(
    name="quit",
    aliases=["q", "exit"],
    description="Exit MathREPL",
    usage=":quit",
    max_args=0,
))

_register(CommandSpec(
    name="units",
    aliases=[],
    description="Toggle physical units mode on/off",
    usage=":units [on|off]",
    max_args=1,
))


# ---------------------------------------------------------------------------
# Help text generation
# ---------------------------------------------------------------------------

def format_help(command_name: str | None = None) -> str:
    """Generate help text for all commands or a specific command."""
    if command_name and command_name in COMMANDS:
        spec = COMMANDS[command_name]
        lines = [
            f"  {spec.usage}",
            f"  {spec.description}",
        ]
        if spec.aliases:
            lines.append(f"  Aliases: {', '.join(':' + a for a in spec.aliases)}")
        return "\n".join(lines)

    # Full help
    seen: set[str] = set()
    lines = [
        "MathREPL Commands:",
        "",
        "  Expression syntax:",
        "    2x + 3x              implicit multiplication",
        "    x^2                  exponentiation (also x**2)",
        "    d/dx(sin(x))         derivative",
        "    integrate(x^2, x)    integration",
        "    limit(sin(x)/x, x, 0)  limits",
        "    series(exp(x), x, 0, 5) Taylor series",
        "    solve(x^2 - 1, x)   solve equations",
        "    f(x) := x^2 + 1     define functions",
        "    N(pi, 50)            numeric eval (50 digits)",
        "    expr =               numeric eval (trailing =)",
        "    x^2 - 1 == 0         equation solving",
        "    plot(sin(x), (x, 0, 10))  plot functions",
        "",
        "  Commands:",
    ]
    for name, spec in COMMANDS.items():
        if name in seen:
            continue
        seen.add(name)
        for alias in spec.aliases:
            seen.add(alias)
        alias_str = ""
        if spec.aliases:
            alias_str = f"  (aliases: {', '.join(':' + a for a in spec.aliases)})"
        lines.append(f"    {spec.usage:<30s} {spec.description}{alias_str}")

    return "\n".join(lines)
