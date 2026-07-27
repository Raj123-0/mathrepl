"""Tests for the engine/evaluator module.

Covers:
- Symbolic simplification
- Variable substitution
- Function definition and application
- Equation solving
"""

from __future__ import annotations

import sympy
from sympy import Symbol, cos, sin, sqrt

from mathrepl.engine.evaluator import ResultKind, evaluate
from mathrepl.parser.tokenizer import tokenize
from mathrepl.session.state import SessionState


class TestSymbolicEvaluation:
    """Tests that expressions are simplified correctly."""

    def test_simple_addition(self) -> None:
        parsed = tokenize("2*x + 3*x")
        result = evaluate(parsed, {}, {})
        assert result.kind == ResultKind.SYMBOLIC
        x = Symbol("x")
        assert result.symbolic == 5 * x  # type: ignore

    def test_polynomial_simplification(self) -> None:
        parsed = tokenize("(x + 1)^2")
        result = evaluate(parsed, {}, {})
        assert result.kind == ResultKind.SYMBOLIC
        # Should be x**2 + 2*x + 1 or (x + 1)**2 — both are valid
        assert result.symbolic is not None

    def test_trig_identity(self) -> None:
        parsed = tokenize("sin(x)^2 + cos(x)^2")
        result = evaluate(parsed, {}, {})
        assert result.kind == ResultKind.SYMBOLIC
        # The best simplification should give 1
        assert result.symbolic == 1

    def test_derivative(self) -> None:
        parsed = tokenize("diff(sin(x), x)")
        result = evaluate(parsed, {}, {})
        assert result.kind == ResultKind.SYMBOLIC
        assert result.symbolic == cos(Symbol("x"))

    def test_integration(self) -> None:
        parsed = tokenize("integrate(x^2, x)")
        result = evaluate(parsed, {}, {})
        assert result.kind == ResultKind.SYMBOLIC
        x = Symbol("x")
        assert result.symbolic == x**3 / 3  # type: ignore


class TestVariableSubstitution:
    """Tests that session variables are properly substituted."""

    def test_variable_in_expression(self) -> None:
        variables: dict[str, sympy.Basic] = {"a": sympy.Integer(5)}
        parsed = tokenize("a + 1")
        result = evaluate(parsed, variables, {})
        assert result.kind == ResultKind.SYMBOLIC
        assert result.symbolic == 6

    def test_variable_assignment(self) -> None:
        parsed = tokenize("a = 42")
        result = evaluate(parsed, {}, {})
        assert result.kind == ResultKind.ASSIGNMENT
        assert result.assign_target == "a"
        assert result.assign_value == 42


class TestFunctionDefinition:
    """Tests for user-defined functions."""

    def test_define_function(self) -> None:
        parsed = tokenize("f(x) := x^2 + 1")
        result = evaluate(parsed, {}, {})
        assert result.kind == ResultKind.FUNC_DEFINITION
        assert result.func_name == "f"


class TestEquationSolving:
    """Tests for equation solving."""

    def test_quadratic(self) -> None:
        parsed = tokenize("x^2 - 1 == 0")
        result = evaluate(parsed, {}, {})
        assert result.kind == ResultKind.EQUATION_SOLUTION
        assert result.solutions is not None
        # Solutions should be -1 and 1
        assert set(result.solutions) == {-1, 1}

    def test_linear(self) -> None:
        parsed = tokenize("2*x + 4 == 0")
        result = evaluate(parsed, {}, {})
        assert result.kind == ResultKind.EQUATION_SOLUTION
        assert result.solutions == [-2]


class TestNumericEvaluation:
    """Tests for numeric evaluation."""

    def test_n_pi(self) -> None:
        parsed = tokenize("N(pi)")
        result = evaluate(parsed, {}, {}, precision=15)
        assert result.kind == ResultKind.NUMERIC
        assert result.numeric is not None
        # Should be approximately 3.14159...
        assert str(result.numeric).startswith("3.14159")

    def test_n_with_precision(self) -> None:
        parsed = tokenize("N(pi, 50)")
        result = evaluate(parsed, {}, {}, precision=15)
        assert result.kind == ResultKind.NUMERIC
        num_str = str(result.numeric)
        # Should have many digits
        assert len(num_str) > 30

    def test_trailing_equals(self) -> None:
        parsed = tokenize("sqrt(2) =")
        result = evaluate(parsed, {}, {}, precision=15)
        assert result.kind == ResultKind.NUMERIC
        assert str(result.numeric).startswith("1.41421")


class TestErrorHandling:
    """Tests that errors are handled gracefully."""

    def test_invalid_expression(self) -> None:
        parsed = tokenize("+++")
        result = evaluate(parsed, {}, {})
        assert result.kind == ResultKind.ERROR
