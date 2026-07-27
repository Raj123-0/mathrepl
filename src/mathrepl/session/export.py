"""Export sessions to LaTeX documents and Jupyter notebooks.

This makes the "living notebook" concept literal — what happens in the
terminal can become a shareable document.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import sympy

from mathrepl.session.state import HistoryEntry, SessionState


# ---------------------------------------------------------------------------
# LaTeX export
# ---------------------------------------------------------------------------

def export_latex(
    state: SessionState,
    path: str | Path | None = None,
    *,
    entries: list[int] | None = None,
) -> Path:
    """Export session history to a standalone LaTeX document.

    Parameters
    ----------
    state:
        The session to export.
    path:
        Output file path.  Defaults to ``./mathrepl_session.tex``.
    entries:
        Optional list of history indices to include.  ``None`` = all.

    Returns
    -------
    Path
        The resolved file path that was written.
    """
    filepath = Path(path) if path else Path("mathrepl_session.tex")

    history = _filter_entries(state.history, entries)

    lines: list[str] = [
        r"\documentclass[11pt]{article}",
        r"\usepackage{amsmath, amssymb, amsfonts}",
        r"\usepackage[margin=1in]{geometry}",
        r"\usepackage{fancyhdr}",
        r"\pagestyle{fancy}",
        r"\title{MathREPL Session}",
        r"\date{\today}",
        r"\begin{document}",
        r"\maketitle",
        "",
    ]

    for entry in history:
        lines.append(f"% --- Entry {entry.index} ---")
        lines.append(r"\noindent")
        lines.append(f"\\textbf{{In [{entry.index}]:}} \\verb|{_escape_latex_verb(entry.input_str)}|")
        lines.append("")

        # Try to convert the output to LaTeX via sympy
        latex_output = _try_sympy_latex(entry.output_repr)
        if latex_output:
            lines.append(f"\\textbf{{Out[{entry.index}]:}}")
            lines.append(r"\begin{align*}")
            lines.append(f"  & {latex_output}")
            lines.append(r"\end{align*}")
        else:
            lines.append(
                f"\\textbf{{Out[{entry.index}]:}} \\verb|{_escape_latex_verb(entry.output_repr)}|"
            )
        lines.append(r"\bigskip")
        lines.append("")

    lines.append(r"\end{document}")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath.resolve()


# ---------------------------------------------------------------------------
# Jupyter export
# ---------------------------------------------------------------------------

def export_jupyter(
    state: SessionState,
    path: str | Path | None = None,
    *,
    entries: list[int] | None = None,
) -> Path:
    """Export session history to a Jupyter notebook (``.ipynb``).

    Parameters
    ----------
    state:
        The session to export.
    path:
        Output file path.  Defaults to ``./mathrepl_session.ipynb``.
    entries:
        Optional list of history indices to include.  ``None`` = all.

    Returns
    -------
    Path
        The resolved file path that was written.

    Raises
    ------
    ImportError
        If ``nbformat`` is not installed.
    """
    try:
        import nbformat as nbf  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "Jupyter export requires the 'nbformat' package.\n"
            "Install it with: pip install mathrepl[export]"
        ) from exc

    filepath = Path(path) if path else Path("mathrepl_session.ipynb")

    history = _filter_entries(state.history, entries)

    nb = nbf.v4.new_notebook()  # type: ignore[attr-defined]
    cells: list[Any] = []

    # Title cell
    cells.append(nbf.v4.new_markdown_cell(  # type: ignore[attr-defined]
        "# MathREPL Session\n\n"
        "This notebook was exported from an interactive MathREPL session."
    ))

    # Setup cell
    cells.append(nbf.v4.new_code_cell(  # type: ignore[attr-defined]
        "from sympy import *\n"
        "init_printing(use_unicode=True)\n"
        "x, y, z, t = symbols('x y z t')\n"
    ))

    for entry in history:
        # Each history entry becomes a code cell
        code = _convert_to_sympy_code(entry.input_str)
        cells.append(nbf.v4.new_code_cell(code))  # type: ignore[attr-defined]

    nb["cells"] = cells

    filepath.write_text(
        nbf.writes(nb),  # type: ignore[attr-defined]
        encoding="utf-8",
    )
    return filepath.resolve()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filter_entries(
    history: list[HistoryEntry],
    indices: list[int] | None,
) -> list[HistoryEntry]:
    """Filter history entries by index."""
    if indices is None:
        return history
    index_set = set(indices)
    return [e for e in history if e.index in index_set]


def _try_sympy_latex(output_repr: str) -> str | None:
    """Try to parse *output_repr* back into a sympy expression and render LaTeX."""
    try:
        expr = sympy.sympify(output_repr)
        return sympy.latex(expr)
    except Exception:  # noqa: BLE001
        return None


def _escape_latex_verb(text: str) -> str:
    """Escape text for use in a LaTeX ``\\verb`` command."""
    # Replace | with another delimiter if present
    return text.replace("|", "\\textbar{}")


def _convert_to_sympy_code(input_str: str) -> str:
    """Convert a MathREPL input line to valid Python/sympy code.

    Best-effort translation:
    - ``^`` → ``**``
    - ``:=`` → ``=`` (assignment)
    - ``d/dx(...)`` → ``diff(..., x)``
    """
    code = input_str.strip()

    # Function definition: f(x) := expr  →  f = lambda x: expr
    import re  # noqa: PLC0415

    m = re.match(r"^(\w+)\s*\(([^)]+)\)\s*:=\s*(.+)$", code)
    if m:
        name, params, body = m.group(1), m.group(2), m.group(3)
        body = body.replace("^", "**")
        return f"{name} = Lambda(({params},), {body})"

    # Assignment
    code = code.replace(":=", "=")
    # Caret
    code = code.replace("^", "**")

    # Derivative shorthand
    code = re.sub(r"d/d(\w)\((.+)\)", r"diff(\2, \1)", code)

    # Trailing =  (numeric eval) → .evalf()
    if code.endswith("=") and "==" not in code:
        code = code[:-1].strip() + ".evalf()"

    return code
