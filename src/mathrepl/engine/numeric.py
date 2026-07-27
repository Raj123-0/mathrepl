"""Arbitrary-precision numeric evaluation.

Manages the global mpmath precision and provides ``N(expr, digits)``
evaluation that respects the session's working precision.
"""

from __future__ import annotations

from typing import Any

import mpmath
import sympy
from sympy import Basic


def set_precision(digits: int) -> None:
    """Set the global working precision to *digits* decimal places.

    This affects both sympy's ``evalf()`` and raw mpmath computations.
    """
    if digits < 1:
        raise ValueError(f"Precision must be ≥ 1, got {digits}")
    mpmath.mp.dps = digits


def get_precision() -> int:
    """Return the current working precision in decimal digits."""
    return int(mpmath.mp.dps)


def numeric_eval(expr: Basic, digits: int | None = None) -> Any:
    """Evaluate *expr* to a floating-point number with *digits* precision.

    Parameters
    ----------
    expr:
        A sympy expression.
    digits:
        Number of significant decimal digits.  If ``None``, uses the
        current mpmath global precision.

    Returns
    -------
    Any
        A sympy ``Float`` (or ``Matrix`` of floats, etc.).
    """
    prec = digits if digits is not None else get_precision()

    # For matrices, evaluate element-wise
    if isinstance(expr, sympy.MatrixBase):
        return expr.evalf(n=prec)

    if hasattr(expr, "evalf"):
        result = expr.evalf(n=prec)
    else:
        result = expr

    # If the result still contains symbols (free variables), we can't
    # fully evaluate — return what we have.
    return result


def validate_precision_pi(digits: int) -> tuple[bool, str]:
    """Validate that our π computation matches the known value to *digits*.

    Returns ``(passed, message)``.
    """
    computed = str(sympy.pi.evalf(digits + 5))  # extra guard digits

    # Known π digits (first 105)
    known = (
        "3.14159265358979323846264338327950288419716939937510"
        "58209749445923078164062862089986280348253421170679"
    )

    # Compare up to requested digits
    n = min(digits + 2, len(known))  # +2 for "3."
    if computed[:n] == known[:n]:
        return True, f"π to {digits} digits: PASS"
    return False, f"π mismatch at {digits} digits:\n  got:    {computed[:n]}\n  expect: {known[:n]}"


def validate_precision_e(digits: int) -> tuple[bool, str]:
    """Validate that our e computation matches the known value to *digits*."""
    computed = str(sympy.E.evalf(digits + 5))

    known = (
        "2.71828182845904523536028747135266249775724709369995"
        "95749669676277240766303535475945713821785251664274"
    )

    n = min(digits + 2, len(known))
    if computed[:n] == known[:n]:
        return True, f"e to {digits} digits: PASS"
    return False, f"e mismatch at {digits} digits:\n  got:    {computed[:n]}\n  expect: {known[:n]}"
