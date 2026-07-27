"""Keyboard shortcuts for the MathREPL TUI.

Binds common actions to key combinations within the prompt_toolkit session.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

if TYPE_CHECKING:
    from prompt_toolkit.key_binding import KeyPressEvent

    from mathrepl.session.state import SessionState


def create_keybindings(
    session_state: SessionState,
    callbacks: dict[str, Any] | None = None,
) -> KeyBindings:
    """Create the key bindings for the MathREPL.

    Parameters
    ----------
    session_state:
        The current session state (for undo, save, etc.).
    callbacks:
        Optional dict of callback functions for specific actions:
        - ``"save"``: Called when Ctrl+S is pressed.
        - ``"clear_screen"``: Called when Ctrl+L is pressed.

    Returns
    -------
    KeyBindings
        The configured key bindings.
    """
    kb = KeyBindings()
    cbs = callbacks or {}

    @kb.add(Keys.ControlL)
    def _clear_screen(event: KeyPressEvent) -> None:
        """Clear the terminal screen."""
        event.app.renderer.clear()
        if "clear_screen" in cbs:
            cbs["clear_screen"]()

    @kb.add(Keys.ControlU)
    def _undo(event: KeyPressEvent) -> None:
        """Undo the last state change."""
        from mathrepl.render.pretty import render_info  # noqa: PLC0415

        if session_state.undo():
            render_info("  ↶ Undone.")
        else:
            render_info("  Nothing to undo.")

    @kb.add(Keys.ControlS)
    def _save(event: KeyPressEvent) -> None:
        """Quick-save the session."""
        if "save" in cbs:
            cbs["save"]()
        else:
            from mathrepl.session.persistence import save_session  # noqa: PLC0415
            from mathrepl.render.pretty import render_info  # noqa: PLC0415

            path = save_session(session_state)
            render_info(f"  Session saved to {path}")

    return kb
