"""Core evaluation pipeline.

Receives parsed input, substitutes session state, simplifies symbolically,
and optionally evaluates numerically.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

import sympy
from sympy import Basic

from mathrepl.parser.tokenizer import (
    InputKind,
    ParseResult,
    parse_to_sympy,
)
from mathrepl.parser.transformer import (
    auto_doit,
    best_simplification,
    resolve_user_functions,
)
from mathrepl.engine.numeric import numeric_eval


class ResultKind(Enum):
    """Classification of an evaluation result."""

    SYMBOLIC = auto()
    NUMERIC = auto()
    ASSIGNMENT = auto()
    FUNC_DEFINITION = auto()
    EQUATION_SOLUTION = auto()
    PLOT = auto()
    INFO = auto()       # Non-math output (help text, variable listing, etc.)
    ERROR = auto()
    EMPTY = auto()


@dataclass
class EvalResult:
    """Result of evaluating a single user input."""

    kind: ResultKind
    symbolic: Basic | None = None
    numeric: Any = None
    text: str = ""
    # For ASSIGNMENT: what was assigned
    assign_target: str = ""
    assign_value: Basic | None = None
    # For FUNC_DEFINITION
    func_name: str = ""
    # For EQUATION_SOLUTION
    solutions: list[Any] | None = None
    # For PLOT: parsed args to hand to the plot renderer
    plot_args: list[str] | None = None


def evaluate(
    parsed: ParseResult,
    variables: dict[str, Basic],
    functions: dict[str, tuple[list[sympy.Symbol], Basic]],
    precision: int = 15,
) -> EvalResult:
    """Evaluate a parsed input in the context of the current session.

    Parameters
    ----------
    parsed:
        The :class:`ParseResult` from the tokenizer.
    variables:
        Session variable bindings (name → sympy expression).
    functions:
        Session function definitions (name → (params, body)).
    precision:
        Current working precision in decimal digits.

    Returns
    -------
    EvalResult
        The evaluation outcome.
    """
    match parsed.kind:
        case InputKind.EMPTY:
            return EvalResult(kind=ResultKind.EMPTY)

        case InputKind.COMMAND:
            # Commands are handled by the TUI layer, not the engine
            return EvalResult(kind=ResultKind.INFO, text="")

        case InputKind.PLOT:
            return EvalResult(
                kind=ResultKind.PLOT,
                plot_args=parsed.plot_args,
                text=parsed.command,
            )

        case InputKind.EXPRESSION:
            return _eval_expression(parsed, variables, functions)

        case InputKind.NUMERIC_EVAL:
            return _eval_numeric(parsed, variables, functions, precision)

        case InputKind.ASSIGNMENT:
            return _eval_assignment(parsed, variables, functions)

        case InputKind.FUNC_DEFINITION:
            return _eval_func_def(parsed, variables, functions)

        case InputKind.EQUATION:
            return _eval_equation(parsed, variables, functions)

        case _:  # pragma: no cover
            return EvalResult(
                kind=ResultKind.ERROR,
                text=f"Unknown input kind: {parsed.kind}",
            )


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def _build_local_dict(
    variables: dict[str, Basic],
    functions: dict[str, tuple[list[sympy.Symbol], Basic]],
) -> dict[str, Any]:
    """Build the local_dict for parse_to_sympy from session state."""
    local: dict[str, Any] = {}
    # Add variables
    for name, value in variables.items():
        local[name] = value
    # Add function symbols (so the parser recognises them)
    for name in functions:
        local[name] = sympy.Function(name)
    return local


def _parse_and_resolve(
    expr_str: str,
    variables: dict[str, Basic],
    functions: dict[str, tuple[list[sympy.Symbol], Basic]],
) -> Basic:
    """Parse expression string and resolve user functions/variables."""
    local_dict = _build_local_dict(variables, functions)
    expr = parse_to_sympy(expr_str, local_dict)
    expr = resolve_user_functions(expr, functions)
    return expr


def _eval_expression(
    parsed: ParseResult,
    variables: dict[str, Basic],
    functions: dict[str, tuple[list[sympy.Symbol], Basic]],
) -> EvalResult:
    """Evaluate a plain expression symbolically."""
    try:
        expr = _parse_and_resolve(parsed.expr_str, variables, functions)
        expr = auto_doit(expr)
        expr = best_simplification(expr)
        return EvalResult(kind=ResultKind.SYMBOLIC, symbolic=expr)
    except Exception as exc:  # noqa: BLE001
        return EvalResult(kind=ResultKind.ERROR, text=str(exc))


def _eval_numeric(
    parsed: ParseResult,
    variables: dict[str, Basic],
    functions: dict[str, tuple[list[sympy.Symbol], Basic]],
    precision: int,
) -> EvalResult:
    """Evaluate an expression numerically."""
    try:
        expr = _parse_and_resolve(parsed.expr_str, variables, functions)
        expr = auto_doit(expr)
        expr = best_simplification(expr)

        # Use requested precision or session default
        prec = parsed.precision if parsed.precision > 0 else precision
        num = numeric_eval(expr, prec)

        return EvalResult(
            kind=ResultKind.NUMERIC,
            symbolic=expr,
            numeric=num,
        )
    except Exception as exc:  # noqa: BLE001
        return EvalResult(kind=ResultKind.ERROR, text=str(exc))


def _eval_assignment(
    parsed: ParseResult,
    variables: dict[str, Basic],
    functions: dict[str, tuple[list[sympy.Symbol], Basic]],
) -> EvalResult:
    """Evaluate a variable assignment: ``a = expr``."""
    try:
        expr = _parse_and_resolve(parsed.expr_str, variables, functions)
        expr = auto_doit(expr)
        expr = best_simplification(expr)
        return EvalResult(
            kind=ResultKind.ASSIGNMENT,
            symbolic=expr,
            assign_target=parsed.assign_target,
            assign_value=expr,
        )
    except Exception as exc:  # noqa: BLE001
        return EvalResult(kind=ResultKind.ERROR, text=str(exc))


def _eval_func_def(
    parsed: ParseResult,
    variables: dict[str, Basic],
    functions: dict[str, tuple[list[sympy.Symbol], Basic]],
) -> EvalResult:
    """Evaluate a function definition: ``f(x) := expr``."""
    try:
        # Parse the body with the parameters as symbols
        param_symbols = [sympy.Symbol(p) for p in parsed.func_params]
        local_dict = _build_local_dict(variables, functions)
        for sym in param_symbols:
            local_dict[str(sym)] = sym

        body = parse_to_sympy(parsed.expr_str, local_dict)
        body = auto_doit(body)
        body = best_simplification(body)

        return EvalResult(
            kind=ResultKind.FUNC_DEFINITION,
            symbolic=body,
            func_name=parsed.func_name,
        )
    except Exception as exc:  # noqa: BLE001
        return EvalResult(kind=ResultKind.ERROR, text=str(exc))


def _eval_equation(
    parsed: ParseResult,
    variables: dict[str, Basic],
    functions: dict[str, tuple[list[sympy.Symbol], Basic]],
) -> EvalResult:
    """Solve an equation: ``expr == 0``."""
    try:
        expr = _parse_and_resolve(parsed.expr_str, variables, functions)
        expr = auto_doit(expr)

        var = sympy.Symbol(parsed.solve_var)
        solutions = sympy.solve(expr, var)

        return EvalResult(
            kind=ResultKind.EQUATION_SOLUTION,
            symbolic=expr,
            solutions=solutions,
        )
    except Exception as exc:  # noqa: BLE001
        return EvalResult(kind=ResultKind.ERROR, text=str(exc))
