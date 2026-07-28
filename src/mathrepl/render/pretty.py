"""Pretty-print symbolic results using Unicode math rendering.

Wraps sympy's ``pretty()`` with Rich console colouring for a polished
terminal experience.  Input/output numbered like IPython: ``In [1]:`` / ``Out[1]:``.
"""

from __future__ import annotations

from typing import Any

import sympy
from rich.console import Console
from rich.text import Text
from rich.theme import Theme

from mathrepl.engine.evaluator import EvalResult, ResultKind

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

MATHREPL_THEME = Theme({
    "prompt.in": "bold cyan",
    "prompt.out": "bold green",
    "result.symbolic": "white",
    "result.numeric": "bold yellow",
    "result.assignment": "bold magenta",
    "result.function": "bold blue",
    "result.solution": "bold green",
    "error": "bold red",
    "info": "dim white",
    "command": "bold dim cyan",
})

_console = Console(theme=MATHREPL_THEME, highlight=False)


def get_console() -> Console:
    """Return the shared Rich console instance."""
    return _console


def render_result(result: EvalResult, index: int) -> None:
    """Pretty-print an evaluation result to the terminal."""
    match result.kind:
        case ResultKind.EMPTY:
            return

        case ResultKind.SYMBOLIC:
            sym_str = _pretty(result.symbolic)
            _print_out(index, sym_str, "result.symbolic")

        case ResultKind.NUMERIC:
            # Show both symbolic and numeric
            if result.symbolic is not None and result.symbolic != result.numeric:
                sym_str = _pretty(result.symbolic)
                num_str = str(result.numeric)
                _print_out(index, f"{sym_str}\n  ≈ {num_str}", "result.numeric")
            else:
                _print_out(index, str(result.numeric), "result.numeric")

        case ResultKind.ASSIGNMENT:
            sym_str = _pretty(result.assign_value)
            _print_aligned(
                f"  {result.assign_target} ← ", 
                "result.assignment", 
                sym_str, 
                "result.symbolic"
            )

        case ResultKind.FUNC_DEFINITION:
            sym_str = _pretty(result.symbolic)
            _print_aligned(
                f"  {result.func_name}(…) defined: ", 
                "result.function", 
                sym_str, 
                "result.symbolic"
            )

        case ResultKind.EQUATION_SOLUTION:
            if result.solutions:
                for i, sol in enumerate(result.solutions):
                    label = f"  x₍{i + 1}₎ = " if len(result.solutions) > 1 else "  x = "
                    sym_str = _pretty(sol)
                    _print_aligned(
                        label, 
                        "result.solution", 
                        sym_str, 
                        "result.symbolic"
                    )
            else:
                _console.print("  No solutions found.", style="info")

        case ResultKind.ERROR:
            _console.print(f"  Error: {result.text}", style="error")

        case ResultKind.INFO:
            if result.text:
                _console.print(result.text, style="info")

        case ResultKind.PLOT:
            pass  # Handled by the TUI layer via plots.py

        case _:
            _console.print(f"  {result}", style="info")


def render_prompt(index: int) -> str:
    """Return the formatted input prompt string."""
    return f"In [{index}]: "


def render_error(message: str) -> None:
    """Print an error message."""
    _console.print(f"  Error: {message}", style="error")


def render_info(message: str) -> None:
    """Print an informational message."""
    _console.print(message, style="info")


def render_welcome() -> None:
    """Print the welcome banner."""
    from mathrepl import __version__  # noqa: PLC0415

    banner = f"""
[bold cyan]╔══════════════════════════════════════════════╗
║                [bold white]MathREPL v{__version__}[bold cyan]               ║
║      [dim white]Interactive Symbolic Math Notebook[bold cyan]      ║
╚══════════════════════════════════════════════╝[/]

[dim]  Type math expressions, e.g. [white]2x + 3x[/dim][dim], [white]d/dx(sin(x))[/dim]
[dim]  Define functions: [white]f(x) := x^2 + 1[/dim]
[dim]  Numeric eval: [white]N(pi, 50)[/dim][dim] or [white]expr =[/dim]
[dim]  Type [cyan]:help[/dim][dim] for all commands, [cyan]:quit[/dim][dim] to exit.[/dim]
"""
    _console.print(banner)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pretty(expr: Any) -> str:
    """Pretty-print a sympy expression using Unicode."""
    if expr is None:
        return ""
    try:
        return sympy.pretty(expr, use_unicode=True)
    except Exception:  # noqa: BLE001
        return str(expr)


def _print_aligned(prefix: str, prefix_style: str, text: str, text_style: str) -> None:
    """Print text. If multiline, print prefix on its own line, then text indented."""
    lines = text.split("\n")
    if len(lines) == 1:
        _console.print(
            Text(prefix, style=prefix_style),
            Text(lines[0], style=text_style),
            sep="",
        )
    else:
        _console.print(Text(prefix, style=prefix_style))
        for line in lines:
            _console.print(
                Text("    "),
                Text(line, style=text_style),
                sep="",
            )


def _print_out(index: int, text: str, style: str) -> None:
    """Print a numbered output line."""
    prefix = f"Out[{index}]: "
    _print_aligned(prefix, "prompt.out", text, style)
