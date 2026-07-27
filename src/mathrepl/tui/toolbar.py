"""Bottom toolbar for the MathREPL TUI.

Shows current precision, variable count, and keyboard shortcut hints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text import HTML

if TYPE_CHECKING:
    from mathrepl.session.state import SessionState


def create_toolbar(session_state: SessionState) -> object:
    """Create a bottom toolbar callable for prompt_toolkit.

    Returns a callable that prompt_toolkit invokes on every render cycle
    to update the toolbar content.
    """

    def _toolbar() -> HTML:
        n_vars = len(session_state.variables)
        n_funcs = len(session_state.functions)
        prec = session_state.precision

        parts: list[str] = [
            f"<b>Precision:</b> {prec}",
            f"<b>Vars:</b> {n_vars}",
            f"<b>Funcs:</b> {n_funcs}",
        ]

        shortcuts = (
            "<ansicyan>[Ctrl+S]</ansicyan> save  "
            "<ansicyan>[Ctrl+U]</ansicyan> undo  "
            "<ansicyan>[Ctrl+L]</ansicyan> clear  "
            "<ansicyan>[Ctrl+D]</ansicyan> quit"
        )

        left = " │ ".join(parts)
        return HTML(
            f"<style bg='#1e293b' fg='#94a3b8'> {left}  │  {shortcuts} </style>"
        )

    return _toolbar
