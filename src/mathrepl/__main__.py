"""Entry point for ``python -m mathrepl`` and the ``mathrepl`` console script."""

from __future__ import annotations


import sys
from pathlib import Path

def main() -> None:
    """Launch the MathREPL interactive shell."""
    # Ensure stdout handles Unicode (critical for Windows terminals)
    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore
        except (AttributeError, TypeError):
            pass

    # Lazy-import the TUI so cold startup stays fast when this module is
    # merely *imported* (e.g. by test infrastructure).
    from mathrepl.tui.app import run_repl  # noqa: PLC0415

    run_repl()


if __name__ == "__main__":
    # If run directly as a script (e.g., via IDE "Run" button), the 'src' directory
    # might not be in sys.path. We add it here so 'import mathrepl' works.
    if not __package__:
        src_dir = str(Path(__file__).resolve().parent.parent)
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

    main()
