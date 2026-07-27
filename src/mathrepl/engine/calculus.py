"""Calculus operations — differentiation, integration, limits, series.

These are thin wrappers around sympy that add:
- Numeric fallback for integrals with no closed form
- Friendly error messages
"""

from __future__ import annotations

from typing import Any

import sympy
from sympy import Basic, Expr, Symbol, oo


def differentiate(expr: Basic, var: Symbol, order: int = 1) -> Basic:
    """Compute the *n*-th derivative of *expr* w.r.t. *var*."""
    return sympy.diff(expr, var, order)


def integrate_expr(
    expr: Basic,
    var: Symbol,
    limits: tuple[Any, Any] | None = None,
    precision: int = 15,
) -> Basic | str:
    """Integrate *expr* w.r.t. *var*, optionally over *limits*.

    Parameters
    ----------
    expr:
        The integrand.
    var:
        Variable of integration.
    limits:
        ``(lower, upper)`` for definite integrals, or ``None`` for indefinite.
    precision:
        Decimal digits for numeric fallback.

    Returns
    -------
    Basic | str
        The symbolic result, or a string with the numeric approximation
        if no closed form exists.
    """
    if limits is not None:
        lower, upper = limits
        result = sympy.integrate(expr, (var, lower, upper))

        # If sympy returned an unevaluated Integral, try numeric fallback
        if result.has(sympy.Integral):
            try:
                import mpmath  # noqa: PLC0415

                f = sympy.lambdify(var, expr, modules=["mpmath"])
                with mpmath.workdps(precision):
                    numeric = mpmath.quad(f, [float(lower), float(upper)])
                return sympy.Float(str(numeric), precision)
            except Exception:  # noqa: BLE001
                pass  # Return the unevaluated integral
        return result
    else:
        return sympy.integrate(expr, var)


def compute_limit(
    expr: Basic,
    var: Symbol,
    point: Any,
    direction: str = "+-",
) -> Basic:
    """Compute the limit of *expr* as *var* → *point*."""
    if direction == "+-":
        return sympy.limit(expr, var, point)
    return sympy.limit(expr, var, point, direction)


def compute_series(
    expr: Basic,
    var: Symbol,
    point: Any = 0,
    order: int = 6,
) -> Basic:
    """Compute the Taylor/Laurent series of *expr* around *point*."""
    return sympy.series(expr, var, point, n=order)
