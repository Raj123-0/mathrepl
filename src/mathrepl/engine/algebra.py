"""Algebra operations — equation solving, ODEs, and matrix operations."""

from __future__ import annotations

from typing import Any

from sympy import Basic, Eq, Function, Matrix, Symbol
import sympy




def solve_equation(
    expr: Basic,
    var: Symbol,
    *,
    as_set: bool = False,
) -> list[Any]:
    """Solve an algebraic equation for *var*.

    Parameters
    ----------
    expr:
        Expression equal to zero (i.e. solving ``expr = 0``).
    var:
        The unknown to solve for.
    as_set:
        If ``True``, return a :class:`~sympy.sets.sets.FiniteSet`.
    """
    if as_set:
        result = sympy.solveset(expr, var)
        return [result]
    return sympy.solve(expr, var)  # type: ignore[return-value]


def solve_system(
    equations: list[Basic],
    variables: list[Symbol],
) -> list[dict[Symbol, Any]]:
    """Solve a system of equations."""
    result = sympy.solve(equations, variables, dict=True)
    return result  # type: ignore[return-value]


def solve_ode(
    ode: Basic,
    func: Function | None = None,
) -> Any:
    """Solve an ordinary differential equation.

    Parameters
    ----------
    ode:
        The ODE expression.
    func:
        The unknown function. If ``None``, sympy will try to auto-detect it.
    """
    return sympy.dsolve(ode, func)


def matrix_from_list(data: list[list[Any]]) -> Matrix:
    """Create a sympy Matrix from nested lists."""
    return Matrix(data)


def matrix_determinant(m: Matrix) -> Basic:
    """Compute the determinant of a matrix."""
    return m.det()


def matrix_inverse(m: Matrix) -> Matrix:
    """Compute the inverse of a matrix."""
    return m.inv()


def matrix_eigenvalues(m: Matrix) -> dict[Any, int]:
    """Compute eigenvalues with multiplicities."""
    return m.eigenvals()


def matrix_eigenvectors(m: Matrix) -> list[tuple[Any, int, list[Any]]]:
    """Compute eigenvectors."""
    return m.eigenvects()  # type: ignore[return-value]
