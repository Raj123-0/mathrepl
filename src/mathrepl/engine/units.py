"""Physical units support via sympy.physics.units.

Provides unit-aware expression evaluation and conversion.
"""

from __future__ import annotations

from typing import Any

import sympy
from sympy import Basic
from sympy.physics.units import (
    Quantity,
    convert_to,
    # SI base units
    meter,
    kilogram,
    second,
    ampere,
    kelvin,
    mole,
    candela,
    # Derived units
    newton,
    joule,
    watt,
    pascal,
    hertz,
    coulomb,
    volt,
    ohm,
    farad,
    # Common prefixes
    kilo,
    mega,
    giga,
    milli,
    micro,
    nano,
    # Non-SI
    speed_of_light,
    gravitational_constant,
)


# ---------------------------------------------------------------------------
# Unit namespace for the parser
# ---------------------------------------------------------------------------

UNIT_NAMES: dict[str, Any] = {
    # SI base
    "meter": meter,
    "m": meter,
    "kilogram": kilogram,
    "kg": kilogram,
    "second": second,
    "s": second,
    "ampere": ampere,
    "A": ampere,
    "kelvin": kelvin,
    "K": kelvin,
    "mole": mole,
    "mol": mole,
    "candela": candela,
    "cd": candela,
    # Derived
    "newton": newton,
    "N_unit": newton,  # Avoid clash with N() numeric eval
    "joule": joule,
    "J": joule,
    "watt": watt,
    "W": watt,
    "pascal": pascal,
    "Pa": pascal,
    "hertz": hertz,
    "Hz": hertz,
    "coulomb": coulomb,
    "C": coulomb,
    "volt": volt,
    "V": volt,
    "ohm": ohm,
    "farad": farad,
    "F": farad,
    # Length
    "km": kilo * meter,
    "cm": sympy.Rational(1, 100) * meter,
    "mm": milli * meter,
    "um": micro * meter,
    "nm": nano * meter,
    # Mass
    "g": milli * kilogram,
    "mg": micro * kilogram,
    # Time
    "ms": milli * second,
    "us": micro * second,
    "ns": nano * second,
    "minute": 60 * second,
    "hour": 3600 * second,
    # Speed
    "c_light": speed_of_light,
    # Constants
    "G_const": gravitational_constant,
}


def convert_units(expr: Basic, target_unit: Any) -> Basic:
    """Convert an expression with units to *target_unit*.

    Parameters
    ----------
    expr:
        A sympy expression containing unit quantities.
    target_unit:
        The desired output unit(s).
    """
    return convert_to(expr, target_unit)


def has_units(expr: Basic) -> bool:
    """Check whether an expression contains any unit quantities."""
    for sub in sympy.preorder_traversal(expr):
        if isinstance(sub, Quantity):
            return True
    return False
