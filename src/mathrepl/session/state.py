"""Session state — variables, functions, history, and undo stack.

This is the living core of a MathREPL session.  Every state-mutating
operation pushes a snapshot onto the undo stack so that ``:undo`` can
roll back to the previous state.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import sympy
from sympy import Basic, Symbol

from mathrepl.engine.numeric import get_precision, set_precision


@dataclass
class HistoryEntry:
    """A single entry in the session history."""

    index: int
    input_str: str
    output_repr: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class SessionSnapshot:
    """A shallow snapshot of session state for undo."""

    variables: dict[str, Basic]
    functions: dict[str, tuple[list[Symbol], Basic]]
    precision: int


class SessionState:
    """Persistent session state for the MathREPL.

    Tracks:
    - Named variables (``a = 42``)
    - User-defined functions (``f(x) := x^2 + 1``)
    - Input/output history with timestamps
    - Undo stack for rolling back state changes
    - Working precision
    """

    def __init__(self, precision: int = 15) -> None:
        self.variables: dict[str, Basic] = {}
        self.functions: dict[str, tuple[list[Symbol], Basic]] = {}
        self.history: list[HistoryEntry] = []
        self._undo_stack: list[SessionSnapshot] = []
        self._precision: int = precision
        self._entry_counter: int = 0

        # Initialise mpmath precision
        set_precision(precision)

    # -- Properties --------------------------------------------------------

    @property
    def precision(self) -> int:
        return self._precision

    @precision.setter
    def precision(self, value: int) -> None:
        if value < 1:
            raise ValueError(f"Precision must be ≥ 1, got {value}")
        self._push_undo()
        self._precision = value
        set_precision(value)

    @property
    def entry_counter(self) -> int:
        return self._entry_counter

    # -- State mutation (with undo) ----------------------------------------

    def set_variable(self, name: str, value: Basic) -> None:
        """Set a named variable, pushing undo state."""
        self._push_undo()
        self.variables[name] = value

    def set_function(
        self,
        name: str,
        params: list[str],
        body: Basic,
    ) -> None:
        """Define a user function, pushing undo state."""
        self._push_undo()
        param_symbols = [Symbol(p) for p in params]
        self.functions[name] = (param_symbols, body)

    def add_history(self, input_str: str, output_repr: str) -> int:
        """Record a history entry and return its index."""
        self._entry_counter += 1
        entry = HistoryEntry(
            index=self._entry_counter,
            input_str=input_str,
            output_repr=output_repr,
        )
        self.history.append(entry)
        return self._entry_counter

    # -- Undo --------------------------------------------------------------

    def _push_undo(self) -> None:
        """Snapshot the current state onto the undo stack."""
        snapshot = SessionSnapshot(
            variables=copy.copy(self.variables),
            functions=copy.copy(self.functions),
            precision=self._precision,
        )
        self._undo_stack.append(snapshot)
        # Cap the stack at 100 entries
        if len(self._undo_stack) > 100:
            self._undo_stack = self._undo_stack[-100:]

    def undo(self) -> bool:
        """Roll back the last state change.  Returns ``True`` on success."""
        if not self._undo_stack:
            return False
        snapshot = self._undo_stack.pop()
        self.variables = snapshot.variables
        self.functions = snapshot.functions
        self._precision = snapshot.precision
        set_precision(snapshot.precision)
        return True

    # -- Query -------------------------------------------------------------

    def get_history(self, last_n: int | None = None) -> list[HistoryEntry]:
        """Return history entries, optionally limited to the last *n*."""
        if last_n is not None:
            return self.history[-last_n:]
        return list(self.history)

    def clear(self) -> None:
        """Reset all state."""
        self._push_undo()
        self.variables.clear()
        self.functions.clear()
        self.history.clear()
        self._entry_counter = 0

    # -- Serialisation helpers (used by persistence.py) --------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise state to a plain dict (for JSON persistence)."""
        return {
            "version": 1,
            "precision": self._precision,
            "entry_counter": self._entry_counter,
            "variables": {
                name: sympy.srepr(val)
                for name, val in self.variables.items()
            },
            "functions": {
                name: {
                    "params": [str(p) for p in params],
                    "body": sympy.srepr(body),
                }
                for name, (params, body) in self.functions.items()
            },
            "history": [
                {
                    "index": entry.index,
                    "input": entry.input_str,
                    "output": entry.output_repr,
                    "timestamp": entry.timestamp,
                }
                for entry in self.history
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionState":
        """Deserialise state from a dict produced by :meth:`to_dict`."""
        state = cls(precision=data.get("precision", 15))
        state._entry_counter = data.get("entry_counter", 0)

        # Restore variables
        for name, srepr_str in data.get("variables", {}).items():
            state.variables[name] = sympy.sympify(srepr_str)  # type: ignore[assignment]

        # Restore functions
        for name, fdata in data.get("functions", {}).items():
            params = [Symbol(p) for p in fdata["params"]]
            body = sympy.sympify(fdata["body"])
            state.functions[name] = (params, body)  # type: ignore[assignment]

        # Restore history
        for hdata in data.get("history", []):
            entry = HistoryEntry(
                index=hdata["index"],
                input_str=hdata["input"],
                output_repr=hdata["output"],
                timestamp=hdata.get("timestamp", ""),
            )
            state.history.append(entry)

        return state

    def __repr__(self) -> str:
        return (
            f"SessionState(vars={len(self.variables)}, "
            f"funcs={len(self.functions)}, "
            f"history={len(self.history)}, "
            f"precision={self._precision})"
        )
