"""AST transformer — additional rewrites on parsed sympy expressions.

This module applies transformations *after* sympy has parsed the expression,
catching patterns that are easier to handle on the symbolic AST than on raw text.
"""

from __future__ import annotations

import sympy
from sympy import Basic, Derivative, Function, Integral, Symbol


def auto_doit(expr: Basic) -> Basic:
    """Evaluate unevaluated derivatives and integrals where possible.

    If the expression contains unevaluated ``Derivative`` or ``Integral``
    objects, attempt to compute them.  This lets the user write
    ``integrate(x^2, x)`` and immediately see the result rather than the
    unevaluated ``Integral`` object.
    """
    if expr.has(Derivative):
        expr = expr.doit()
    if expr.has(Integral):
        try:
            result = expr.doit()
            # If doit() returned the same Integral unchanged, leave it
            if not result.has(Integral):
                expr = result
        except Exception:  # noqa: BLE001 — sympy can raise many things
            pass
    return expr


def best_simplification(expr: Basic) -> Basic:
    """Try multiple simplification strategies and return the "simplest".

    Strategy: apply several simplifications in parallel and pick the one
    with the smallest leaf count (number of atoms).  This avoids the common
    problem where ``simplify()`` makes an expression *worse*.
    """
    if not isinstance(expr, Basic):
        return expr

    candidates: list[Basic] = [expr]

    try:
        candidates.append(sympy.simplify(expr))
    except Exception:  # noqa: BLE001
        pass

    try:
        candidates.append(sympy.trigsimp(expr))
    except Exception:  # noqa: BLE001
        pass

    try:
        candidates.append(sympy.factor(expr))
    except Exception:  # noqa: BLE001
        pass

    try:
        candidates.append(sympy.cancel(expr))
    except Exception:  # noqa: BLE001
        pass

    # Pick the candidate with the smallest count of operations
    def _complexity(e: Basic) -> int:
        return int(sympy.count_ops(e))  # type: ignore[arg-type]

    return min(candidates, key=_complexity)


def resolve_user_functions(
    expr: Basic,
    functions: dict[str, tuple[list[Symbol], Basic]],
) -> Basic:
    """Substitute user-defined functions into the expression.

    Parameters
    ----------
    expr:
        The parsed expression.
    functions:
        Mapping of ``func_name → (param_symbols, body_expr)``.
        For example, ``{"f": ([x], x**2 + 1)}``.
    """
    if not functions:
        return expr

    for name, (params, body) in functions.items():
        # Create a sympy Function class to match against
        func_cls = Function(name)  # type: ignore[assignment]

        # Walk the expression tree looking for applications of this function
        for sub_expr in sympy.preorder_traversal(expr):
            if (
                isinstance(sub_expr, sympy.core.function.AppliedUndef)
                and sub_expr.func.__name__ == name
                and len(sub_expr.args) == len(params)
            ):
                # Build substitution mapping: param → actual argument
                subs = dict(zip(params, sub_expr.args))
                replacement = body.subs(subs)
                expr = expr.subs(sub_expr, replacement)

    return expr
