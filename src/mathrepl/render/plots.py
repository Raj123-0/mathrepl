"""Plot rendering — dispatches matplotlib plots to the terminal or a window.

Lazy-imports matplotlib only when the first plot is requested to keep
startup fast.  Detects terminal image protocol support and falls back
gracefully.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import sympy
from sympy import Basic, Symbol

from mathrepl.parser.tokenizer import parse_to_sympy


def render_plot(
    plot_args: list[str],
    variables: dict[str, Basic],
    functions: dict[str, tuple[list[Symbol], Basic]],
    *,
    plot_type: str = "plot",
) -> str | None:
    """Render a 2D or 3D plot from parsed plot arguments.

    Parameters
    ----------
    plot_args:
        The parsed plot arguments from the tokenizer.
        E.g. ``['sin(x)', '(x, 0, 10)']``
    variables:
        Session variable bindings.
    functions:
        Session function definitions.
    plot_type:
        ``"plot"`` for 2D, ``"plot3d"`` for 3D.

    Returns
    -------
    str | None
        Path to the saved PNG if inline display is not supported,
        or ``None`` if the plot was shown inline / in a window.
    """
    try:
        import matplotlib  # noqa: PLC0415
        import matplotlib.pyplot as plt  # noqa: PLC0415
    except ImportError:
        return "Error: matplotlib is not installed. Install with: pip install mathrepl[plots]"

    # Parse the expression and range
    if not plot_args:
        return "Error: plot() requires at least an expression argument."

    # Build the local dict for parsing
    from mathrepl.engine.evaluator import _build_local_dict  # noqa: PLC0415

    local_dict = _build_local_dict(variables, functions)

    if plot_type == "plot3d":
        return _render_3d(plot_args, local_dict)
    return _render_2d(plot_args, local_dict)


def _render_2d(
    plot_args: list[str],
    local_dict: dict[str, Any],
) -> str | None:
    """Render a 2D plot."""
    import matplotlib.pyplot as plt  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415

    # Parse expression
    expr_str = plot_args[0]
    expr = parse_to_sympy(expr_str, local_dict)

    # Parse range: default to (x, -10, 10)
    var = Symbol("x")
    x_min, x_max = -10.0, 10.0

    if len(plot_args) > 1:
        range_str = plot_args[1].strip("()")
        parts = [p.strip() for p in range_str.split(",")]
        if len(parts) >= 1:
            var = Symbol(parts[0])
        if len(parts) >= 2:
            x_min = float(sympy.sympify(parts[1]))
        if len(parts) >= 3:
            x_max = float(sympy.sympify(parts[2]))

    # Create the numerical function
    f = sympy.lambdify(var, expr, modules=["numpy"])

    # Generate data
    x_data = np.linspace(x_min, x_max, 1000)
    try:
        y_data = f(x_data)
    except Exception as exc:  # noqa: BLE001
        return f"Error evaluating expression for plot: {exc}"

    # Plot with a clean style
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x_data, y_data, linewidth=2, color="#00d4aa")
    ax.set_xlabel(str(var), fontsize=12)
    ax.set_title(str(expr), fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.set_facecolor("#1a1a2e")
    fig.patch.set_facecolor("#16213e")
    ax.tick_params(colors="white")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    ax.title.set_color("white")
    for spine in ax.spines.values():
        spine.set_color("#444")

    return _show_or_save(fig)


def _render_3d(
    plot_args: list[str],
    local_dict: dict[str, Any],
) -> str | None:
    """Render a 3D surface plot."""
    import matplotlib.pyplot as plt  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415

    expr_str = plot_args[0]
    expr = parse_to_sympy(expr_str, local_dict)

    # Parse ranges
    x_var, y_var = Symbol("x"), Symbol("y")
    x_min, x_max = -5.0, 5.0
    y_min, y_max = -5.0, 5.0

    if len(plot_args) > 1:
        r1 = plot_args[1].strip("()")
        parts = [p.strip() for p in r1.split(",")]
        if parts:
            x_var = Symbol(parts[0])
        if len(parts) >= 2:
            x_min = float(sympy.sympify(parts[1]))
        if len(parts) >= 3:
            x_max = float(sympy.sympify(parts[2]))

    if len(plot_args) > 2:
        r2 = plot_args[2].strip("()")
        parts = [p.strip() for p in r2.split(",")]
        if parts:
            y_var = Symbol(parts[0])
        if len(parts) >= 2:
            y_min = float(sympy.sympify(parts[1]))
        if len(parts) >= 3:
            y_max = float(sympy.sympify(parts[2]))

    f = sympy.lambdify((x_var, y_var), expr, modules=["numpy"])

    x_data = np.linspace(x_min, x_max, 100)
    y_data = np.linspace(y_min, y_max, 100)
    X, Y = np.meshgrid(x_data, y_data)

    try:
        Z = f(X, Y)
    except Exception as exc:  # noqa: BLE001
        return f"Error evaluating expression for 3D plot: {exc}"

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(X, Y, Z, cmap="viridis", alpha=0.9)  # type: ignore[attr-defined]
    ax.set_xlabel(str(x_var))  # type: ignore[attr-defined]
    ax.set_ylabel(str(y_var))  # type: ignore[attr-defined]
    ax.set_title(str(expr))  # type: ignore[attr-defined]

    return _show_or_save(fig)


def _show_or_save(fig: Any) -> str | None:
    """Try to show the figure inline or fall back to window/file."""
    import matplotlib.pyplot as plt  # noqa: PLC0415

    # Check for inline-capable terminal protocols
    term_program = os.environ.get("TERM_PROGRAM", "")
    is_kitty = "kitty" in term_program.lower()
    is_iterm2 = "iterm" in term_program.lower()

    if is_kitty or is_iterm2:
        # Try to use kitcat or similar inline backend
        try:
            _show_inline_kitty(fig)
            plt.close(fig)
            return None
        except Exception:  # noqa: BLE001
            pass

    # Try regular plt.show() (opens a window)
    try:
        plt.show()
        plt.close(fig)
        return None
    except Exception:  # noqa: BLE001
        pass

    # Last resort: save to temp file
    tmp = Path(tempfile.mkdtemp()) / "mathrepl_plot.png"
    fig.savefig(str(tmp), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return f"Plot saved to: {tmp}"


def _show_inline_kitty(fig: Any) -> None:
    """Display figure inline using the Kitty graphics protocol."""
    import base64  # noqa: PLC0415
    import io  # noqa: PLC0415
    import sys  # noqa: PLC0415

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    data = base64.standard_b64encode(buf.read()).decode("ascii")

    # Kitty graphics protocol
    # Split into chunks of 4096 bytes
    chunk_size = 4096
    chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

    for i, chunk in enumerate(chunks):
        is_last = i == len(chunks) - 1
        m = 0 if is_last else 1
        if i == 0:
            sys.stdout.write(f"\033_Ga=T,f=100,m={m};{chunk}\033\\")
        else:
            sys.stdout.write(f"\033_Gm={m};{chunk}\033\\")

    sys.stdout.write("\n")
    sys.stdout.flush()
