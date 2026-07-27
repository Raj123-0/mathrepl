"""Tab-completion for MathREPL.

Completes:
- Math functions (sin, cos, integrate, …)
- User-defined variables and functions from session state
- Colon-commands (:help, :undo, …)
- Constants (pi, e, oo, …)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

if TYPE_CHECKING:
    from mathrepl.session.state import SessionState


# ---------------------------------------------------------------------------
# Static completion lists
# ---------------------------------------------------------------------------

_MATH_FUNCTIONS: list[str] = [
    "sin", "cos", "tan", "cot", "sec", "csc",
    "asin", "acos", "atan", "atan2",
    "sinh", "cosh", "tanh",
    "exp", "log", "ln", "sqrt", "cbrt",
    "Abs", "sign", "floor", "ceiling",
    "factorial", "gamma", "beta", "binomial",
    "diff", "integrate", "limit", "series",
    "solve", "dsolve",
    "simplify", "expand", "factor", "apart", "together", "cancel", "trigsimp",
    "plot", "plot3d",
    "Derivative", "Integral", "Limit", "Sum", "Product",
    "Matrix", "det", "inv", "transpose",
    "Eq", "N",
    "Function", "Symbol", "symbols",
    "Rational",
]

_CONSTANTS: list[str] = [
    "pi", "e", "I", "oo", "inf", "nan",
    "true", "false",
]

_COMMANDS: list[str] = [
    ":help", ":precision", ":undo", ":history",
    ":vars", ":funcs", ":clear", ":save", ":load",
    ":export", ":quit", ":units",
]


class MathCompleter(Completer):
    """Dynamic completer for the MathREPL prompt.

    Parameters
    ----------
    session_state:
        The current session state, used to dynamically offer completions
        for user-defined variables and functions.
    """

    def __init__(self, session_state: SessionState) -> None:
        self._state = session_state

    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]:
        text = document.text_before_cursor
        # Find the word being typed
        word = self._get_word_before_cursor(text)

        if not word:
            return

        word_lower = word.lower()

        # Colon commands
        if word.startswith(":"):
            for cmd in _COMMANDS:
                if cmd.startswith(word):
                    yield Completion(
                        cmd,
                        start_position=-len(word),
                        display_meta="command",
                    )
            return

        # Math functions
        for func in _MATH_FUNCTIONS:
            if func.lower().startswith(word_lower):
                yield Completion(
                    func,
                    start_position=-len(word),
                    display_meta="function",
                )

        # Constants
        for const in _CONSTANTS:
            if const.lower().startswith(word_lower):
                yield Completion(
                    const,
                    start_position=-len(word),
                    display_meta="constant",
                )

        # User-defined variables
        for var_name in self._state.variables:
            if var_name.lower().startswith(word_lower):
                yield Completion(
                    var_name,
                    start_position=-len(word),
                    display_meta="variable",
                )

        # User-defined functions
        for func_name in self._state.functions:
            if func_name.lower().startswith(word_lower):
                yield Completion(
                    func_name + "(",
                    start_position=-len(word),
                    display_meta="user function",
                )

    @staticmethod
    def _get_word_before_cursor(text: str) -> str:
        """Extract the word being typed at the cursor position."""
        if not text:
            return ""

        # Walk backward to find word start
        i = len(text) - 1
        while i >= 0 and (text[i].isalnum() or text[i] in "_:"):
            i -= 1

        return text[i + 1 :]
