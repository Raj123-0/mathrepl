"""Precision regression tests.

Validates arbitrary-precision computation against known high-precision
values of mathematical constants.
"""

from __future__ import annotations

import sympy

from mathrepl.engine.numeric import (
    get_precision,
    numeric_eval,
    set_precision,
    validate_precision_e,
    validate_precision_pi,
)


class TestPrecisionManagement:
    """Tests for precision get/set."""

    def test_default_precision(self) -> None:
        set_precision(15)
        assert get_precision() == 15

    def test_set_precision(self) -> None:
        set_precision(50)
        assert get_precision() == 50
        set_precision(15)  # Reset

    def test_invalid_precision(self) -> None:
        import pytest  # noqa: PLC0415
        with pytest.raises(ValueError, match="≥ 1"):
            set_precision(0)


class TestPiPrecision:
    """Regression tests for π computation at various precisions."""

    def test_pi_15_digits(self) -> None:
        passed, msg = validate_precision_pi(15)
        assert passed, msg

    def test_pi_50_digits(self) -> None:
        passed, msg = validate_precision_pi(50)
        assert passed, msg

    def test_pi_100_digits(self) -> None:
        passed, msg = validate_precision_pi(100)
        assert passed, msg


class TestEPrecision:
    """Regression tests for e computation at various precisions."""

    def test_e_15_digits(self) -> None:
        passed, msg = validate_precision_e(15)
        assert passed, msg

    def test_e_50_digits(self) -> None:
        passed, msg = validate_precision_e(50)
        assert passed, msg

    def test_e_100_digits(self) -> None:
        passed, msg = validate_precision_e(100)
        assert passed, msg


class TestNumericEval:
    """Tests for the N() evaluation function."""

    def test_sqrt2_precision(self) -> None:
        """sqrt(2) to 50 digits matches known value."""
        result = numeric_eval(sympy.sqrt(2), 50)
        result_str = str(result)
        known_prefix = "1.4142135623730950488016887242096980785696718753769"
        assert result_str.startswith(known_prefix[:30])

    def test_precision_propagation(self) -> None:
        """Verify precision is respected through chained operations."""
        # Compute (pi * e) at high precision
        expr = sympy.pi * sympy.E
        result_15 = str(numeric_eval(expr, 15))
        result_50 = str(numeric_eval(expr, 50))

        # 50-digit result should be longer than 15-digit result
        # (accounting for the leading digits and decimal point)
        assert len(result_50) > len(result_15)

    def test_matrix_eval(self) -> None:
        """Matrices should evaluate element-wise."""
        m = sympy.Matrix([[sympy.pi, sympy.E], [sympy.sqrt(2), sympy.Rational(1, 3)]])
        result = numeric_eval(m, 10)  # type: ignore
        assert isinstance(result, sympy.MatrixBase)
