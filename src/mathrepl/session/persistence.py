"""Session persistence — save and load ``.mathrepl`` session files.

Sessions are stored as JSON using sympy's ``srepr()`` for lossless
round-tripping of symbolic expressions.
"""

from __future__ import annotations

import json
from pathlib import Path

from mathrepl.session.state import SessionState


DEFAULT_FILENAME = "session.mathrepl"


def save_session(state: SessionState, path: str | Path | None = None) -> Path:
    """Save *state* to a ``.mathrepl`` JSON file.

    Parameters
    ----------
    state:
        The session state to persist.
    path:
        File path.  Defaults to ``./session.mathrepl``.

    Returns
    -------
    Path
        The resolved file path that was written.
    """
    filepath = Path(path) if path else Path(DEFAULT_FILENAME)
    if not filepath.suffix:
        filepath = filepath.with_suffix(".mathrepl")

    data = state.to_dict()
    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return filepath.resolve()


def load_session(path: str | Path) -> SessionState:
    """Load a session from a ``.mathrepl`` JSON file.

    Parameters
    ----------
    path:
        Path to the session file.

    Returns
    -------
    SessionState
        The restored session.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If the file is not a valid session.
    """
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"Session file not found: {filepath}")

    text = filepath.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid session file: {exc}") from exc

    if "version" not in data:
        raise ValueError("Session file missing 'version' key — not a MathREPL session?")

    return SessionState.from_dict(data)
