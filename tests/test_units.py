"""Tests for physical units support."""

from __future__ import annotations

from mathrepl.engine.units import UNIT_NAMES, has_units
import sympy


class TestUnitNamespace:
    """Tests that the unit namespace is properly populated."""

    def test_common_units_exist(self) -> None:
        expected = ["meter", "m", "kilogram", "kg", "second", "s", "joule", "J"]
        for name in expected:
            assert name in UNIT_NAMES, f"Unit '{name}' not in namespace"

    def test_prefix_units(self) -> None:
        assert "km" in UNIT_NAMES
        assert "mm" in UNIT_NAMES
        assert "ms" in UNIT_NAMES

    def test_constants(self) -> None:
        assert "c_light" in UNIT_NAMES
        assert "G_const" in UNIT_NAMES


class TestHasUnits:
    """Tests for the has_units detection function."""

    def test_plain_expression(self) -> None:
        x = sympy.Symbol("x")
        assert not has_units(x**2 + 1)  # type: ignore

    def test_expression_with_units(self) -> None:
        from sympy.physics.units import meter, second  # noqa: PLC0415
        expr = 3 * meter / second
        assert has_units(expr)
