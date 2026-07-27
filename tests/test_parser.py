"""Tests for the parser/tokenizer module.

Covers:
- Implicit multiplication
- Derivative shorthand (d/dx)
- Function definitions (:=)
- Numeric evaluation triggers (N(), trailing =)
- Equation detection (==)
- Caret exponentiation
- Command parsing
"""

from __future__ import annotations

import pytest
import sympy
from sympy import Derivative, Symbol, sin

from mathrepl.parser.tokenizer import (
    InputKind,
    ParseResult,
    parse_to_sympy,
    tokenize,
)


# ---------------------------------------------------------------------------
# Input classification
# ---------------------------------------------------------------------------

class TestTokenizeClassification:
    """Tests that input is classified into the correct InputKind."""

    def test_empty_input(self) -> None:
        result = tokenize("")
        assert result.kind == InputKind.EMPTY

    def test_whitespace_only(self) -> None:
        result = tokenize("   ")
        assert result.kind == InputKind.EMPTY

    def test_plain_expression(self) -> None:
        result = tokenize("x^2 + 1")
        assert result.kind == InputKind.EXPRESSION

    def test_command(self) -> None:
        result = tokenize(":help")
        assert result.kind == InputKind.COMMAND
        assert result.command == "help"

    def test_command_with_args(self) -> None:
        result = tokenize(":precision 50")
        assert result.kind == InputKind.COMMAND
        assert result.command == "precision"
        assert result.command_args == ["50"]

    def test_func_definition(self) -> None:
        result = tokenize("f(x) := x^2 + 1")
        assert result.kind == InputKind.FUNC_DEFINITION
        assert result.func_name == "f"
        assert result.func_params == ["x"]

    def test_func_definition_multivar(self) -> None:
        result = tokenize("h(x, y) := x^2 + y^2")
        assert result.kind == InputKind.FUNC_DEFINITION
        assert result.func_name == "h"
        assert result.func_params == ["x", "y"]

    def test_variable_assignment(self) -> None:
        result = tokenize("a = 42")
        assert result.kind == InputKind.ASSIGNMENT
        assert result.assign_target == "a"

    def test_numeric_n_simple(self) -> None:
        result = tokenize("N(pi)")
        assert result.kind == InputKind.NUMERIC_EVAL

    def test_numeric_n_with_digits(self) -> None:
        result = tokenize("N(pi, 50)")
        assert result.kind == InputKind.NUMERIC_EVAL
        assert result.precision == 50

    def test_trailing_equals(self) -> None:
        result = tokenize("pi =")
        assert result.kind == InputKind.NUMERIC_EVAL

    def test_equation(self) -> None:
        result = tokenize("x^2 - 1 == 0")
        assert result.kind == InputKind.EQUATION

    def test_plot(self) -> None:
        result = tokenize("plot(sin(x), (x, 0, 10))")
        assert result.kind == InputKind.PLOT

    def test_plot3d(self) -> None:
        result = tokenize("plot3d(x^2 + y^2, (x, -5, 5), (y, -5, 5))")
        assert result.kind == InputKind.PLOT

    def test_reserved_name_not_assignment(self) -> None:
        """Keywords like ``sin`` should not be treated as assignment targets."""
        result = tokenize("sin = 42")
        # sin is reserved, so this should be a plain expression
        assert result.kind != InputKind.ASSIGNMENT


# ---------------------------------------------------------------------------
# Implicit multiplication
# ---------------------------------------------------------------------------

class TestImplicitMultiplication:
    """Tests for implicit multiplication via sympy transformations."""

    def test_2x(self) -> None:
        expr = parse_to_sympy("2x")
        x = Symbol("x")
        assert expr == 2 * x  # type: ignore

    def test_3sin_x(self) -> None:
        expr = parse_to_sympy("3sin(x)")
        x = Symbol("x")
        assert expr == 3 * sin(x)  # type: ignore

    def test_xy(self) -> None:
        expr = parse_to_sympy("x y")
        x, y = Symbol("x"), Symbol("y")
        assert expr == x * y  # type: ignore


# ---------------------------------------------------------------------------
# Caret exponentiation
# ---------------------------------------------------------------------------

class TestCaretExponentiation:
    def test_x_squared(self) -> None:
        expr = parse_to_sympy("x^2")
        x = Symbol("x")
        assert expr == x**2

    def test_x_cubed(self) -> None:
        expr = parse_to_sympy("x^3")
        x = Symbol("x")
        assert expr == x**3


# ---------------------------------------------------------------------------
# Derivative shorthand
# ---------------------------------------------------------------------------

class TestDerivativeShorthand:
    def test_d_dx_basic(self) -> None:
        result = tokenize("d/dx(x^2)")
        assert "Derivative" in result.expr_str

    def test_d2_dx2(self) -> None:
        result = tokenize("d^2/dx^2(sin(x))")
        assert "Derivative" in result.expr_str

    def test_unicode_superscript(self) -> None:
        result = tokenize("d²/dx²(x^3)")
        assert "Derivative" in result.expr_str
        assert ", 2)" in result.expr_str


# ---------------------------------------------------------------------------
# Absolute value
# ---------------------------------------------------------------------------

class TestAbsValue:
    def test_abs_rewrite(self) -> None:
        result = tokenize("|x|")
        assert "Abs" in result.expr_str


# ---------------------------------------------------------------------------
# ln → log rewrite
# ---------------------------------------------------------------------------

class TestLnRewrite:
    def test_ln_to_log(self) -> None:
        result = tokenize("ln(x)")
        assert "log" in result.expr_str
        assert "ln" not in result.expr_str


# ---------------------------------------------------------------------------
# Plot argument splitting
# ---------------------------------------------------------------------------

class TestPlotParsing:
    def test_plot_args_split(self) -> None:
        result = tokenize("plot(sin(x), (x, 0, 10))")
        assert len(result.plot_args) == 2
        assert result.plot_args[0] == "sin(x)"
        assert result.plot_args[1] == "(x, 0, 10)"

    def test_plot_single_arg(self) -> None:
        result = tokenize("plot(x^2)")
        assert len(result.plot_args) == 1
