"""Shared test fixtures for MathREPL tests."""

from __future__ import annotations

import pytest
import sympy

from mathrepl.session.state import SessionState


@pytest.fixture
def session() -> SessionState:
    """Create a fresh session state for testing."""
    return SessionState(precision=15)


@pytest.fixture
def populated_session() -> SessionState:
    """Create a session with some pre-defined variables and functions."""
    state = SessionState(precision=15)
    state.set_variable("a", sympy.Integer(42))
    state.set_variable("b", sympy.Rational(1, 3))

    x = sympy.Symbol("x")
    state.set_function("f", ["x"], x**2 + 1)  # type: ignore
    state.set_function("g", ["x"], sympy.sin(x))  # type: ignore

    state.add_history("a = 42", "42")
    state.add_history("b = 1/3", "1/3")
    state.add_history("f(x) := x^2 + 1", "x**2 + 1")

    return state
