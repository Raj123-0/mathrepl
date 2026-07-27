"""Tokenizer — pre-processes raw user input before handing to sympy's parser.

Handles:
- Implicit multiplication (``2x`` → ``2*x``)
- Caret exponentiation (``x^2`` → ``x**2``)
- Derivative shorthand (``d/dx(expr)``)
- Assignment syntax (``f(x) := expr``)
- Numeric evaluation triggers (trailing ``=``, ``N(expr)``)
- Equation detection (``expr == 0``)
- Plot command detection
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

import sympy
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


class InputKind(Enum):
    """Classification of user input after tokenization."""

    EXPRESSION = auto()        # Plain expression to evaluate
    ASSIGNMENT = auto()        # Variable assignment: ``a = expr``
    FUNC_DEFINITION = auto()   # Function definition: ``f(x) := expr``
    NUMERIC_EVAL = auto()      # Explicit numeric: ``N(expr)`` or trailing ``=``
    EQUATION = auto()          # Equation to solve: ``expr == 0``
    PLOT = auto()              # Plot command
    COMMAND = auto()           # Colon-command: ``:help``, ``:undo``, …
    EMPTY = auto()             # Blank / whitespace-only input


@dataclass
class ParseResult:
    """Result of tokenizing + classifying user input."""

    kind: InputKind
    raw: str
    # Populated for EXPRESSION / ASSIGNMENT / FUNC_DEFINITION / NUMERIC_EVAL / EQUATION:
    expr_str: str = ""
    # For ASSIGNMENT: the target variable name
    assign_target: str = ""
    # For FUNC_DEFINITION: function name and parameter names
    func_name: str = ""
    func_params: list[str] = field(default_factory=list)
    # For NUMERIC_EVAL: requested precision (0 means "use session default")
    precision: int = 0
    # For EQUATION: the variable to solve for (if detected)
    solve_var: str = ""
    # For PLOT: parsed plot arguments
    plot_args: list[str] = field(default_factory=list)
    # For COMMAND: the command name and arguments
    command: str = ""
    command_args: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Derivative shorthand: d/dx(...), d²/dx²(...), d^2/dx^2(...)
_DERIV_RE = re.compile(
    r"d(?:\^?(\d+)|([²³⁴⁵⁶⁷⁸⁹]))?/"
    r"d([a-zA-Z])(?:\^?(\d+)|([²³⁴⁵⁶⁷⁸⁹]))?"
    r"\s*\((.+)\)",
)

_UNICODE_SUPER_MAP: dict[str, int] = {
    "²": 2, "³": 3, "⁴": 4, "⁵": 5,
    "⁶": 6, "⁷": 7, "⁸": 8, "⁹": 9,
}

# Function definition: f(x) := expr  or  f(x, y) := expr
_FUNC_DEF_RE = re.compile(
    r"^([a-zA-Z_]\w*)\s*\(([^)]+)\)\s*:=\s*(.+)$"
)

# Variable assignment: a = expr  (but NOT  == )
_VAR_ASSIGN_RE = re.compile(
    r"^([a-zA-Z_]\w*)\s*(?<!=)=(?!=)\s*(.+)$"
)

# N(expr) or N(expr, digits)
_NUMERIC_N_RE = re.compile(
    r"^N\s*\(\s*(.+?)(?:\s*,\s*(\d+))?\s*\)$"
)

# Trailing  =  (numeric eval shorthand)
_TRAILING_EQ_RE = re.compile(r"^(.+?)\s*=$")

# Plot commands: plot(...)  /  plot3d(...)
_PLOT_RE = re.compile(r"^(plot3?d?)\s*\((.+)\)$", re.IGNORECASE)

# Equation: contains  ==
_EQUATION_RE = re.compile(r"==")

# Colon-command
_COMMAND_RE = re.compile(r"^:(\w+)(?:\s+(.*))?$")

# Abs value notation:  |expr|  → Abs(expr)
_ABS_RE = re.compile(r"\|([^|]+)\|")

# Factorial:  n!  → factorial(n)
_FACTORIAL_RE = re.compile(r"(\w+)!")


# ---------------------------------------------------------------------------
# Sympy transformation tuple
# ---------------------------------------------------------------------------

TRANSFORMATIONS: tuple[Any, ...] = (
    standard_transformations
    + (implicit_multiplication_application, convert_xor)
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def tokenize(raw_input: str) -> ParseResult:
    """Classify and pre-process a line of user input.

    Returns a :class:`ParseResult` with the input kind, cleaned expression
    string, and any extracted metadata (assignment target, precision, etc.).
    """
    text = raw_input.strip()

    # Empty
    if not text:
        return ParseResult(kind=InputKind.EMPTY, raw=raw_input)

    # Colon-command
    m = _COMMAND_RE.match(text)
    if m:
        cmd = m.group(1).lower()
        args_str = (m.group(2) or "").strip()
        args = args_str.split() if args_str else []
        return ParseResult(
            kind=InputKind.COMMAND,
            raw=raw_input,
            command=cmd,
            command_args=args,
        )

    # Plot command
    m = _PLOT_RE.match(text)
    if m:
        func = m.group(1).lower()
        args_raw = m.group(2)
        return ParseResult(
            kind=InputKind.PLOT,
            raw=raw_input,
            command=func,
            plot_args=_split_plot_args(args_raw),
        )

    # Function definition:  f(x) := expr
    m = _FUNC_DEF_RE.match(text)
    if m:
        name = m.group(1)
        params = [p.strip() for p in m.group(2).split(",")]
        body = m.group(3).strip()
        body = _preprocess(body)
        return ParseResult(
            kind=InputKind.FUNC_DEFINITION,
            raw=raw_input,
            expr_str=body,
            func_name=name,
            func_params=params,
        )

    # N(expr)  or  N(expr, digits)
    m = _NUMERIC_N_RE.match(text)
    if m:
        expr_str = _preprocess(m.group(1))
        digits = int(m.group(2)) if m.group(2) else 0
        return ParseResult(
            kind=InputKind.NUMERIC_EVAL,
            raw=raw_input,
            expr_str=expr_str,
            precision=digits,
        )

    # Trailing  =
    m = _TRAILING_EQ_RE.match(text)
    if m and "==" not in text:
        expr_str = _preprocess(m.group(1))
        return ParseResult(
            kind=InputKind.NUMERIC_EVAL,
            raw=raw_input,
            expr_str=expr_str,
        )

    # Variable assignment:  a = expr  (but not  ==)
    m = _VAR_ASSIGN_RE.match(text)
    if m:
        target = m.group(1)
        # Guard: don't treat sympy builtins as assignment targets
        if target not in _RESERVED_NAMES:
            expr_str = _preprocess(m.group(2))
            return ParseResult(
                kind=InputKind.ASSIGNMENT,
                raw=raw_input,
                expr_str=expr_str,
                assign_target=target,
            )

    # Equation:  expr == expr
    if _EQUATION_RE.search(text):
        # Split on == and form  lhs - rhs
        parts = text.split("==", 1)
        lhs = _preprocess(parts[0].strip())
        rhs = _preprocess(parts[1].strip())
        combined = f"({lhs}) - ({rhs})"
        # Try to detect the variable to solve for
        solve_var = _guess_solve_var(combined)
        return ParseResult(
            kind=InputKind.EQUATION,
            raw=raw_input,
            expr_str=combined,
            solve_var=solve_var,
        )

    # Plain expression
    expr_str = _preprocess(text)
    return ParseResult(
        kind=InputKind.EXPRESSION,
        raw=raw_input,
        expr_str=expr_str,
    )


def parse_to_sympy(
    expr_str: str,
    local_dict: dict[str, Any] | None = None,
) -> sympy.Basic:
    """Parse a pre-processed expression string into a sympy expression.

    Parameters
    ----------
    expr_str:
        The expression string, already run through :func:`_preprocess`.
    local_dict:
        Additional name→value mappings (session variables, user functions).
    """
    if local_dict is None:
        local_dict = {}

    # Merge standard sympy names so users can write ``pi``, ``e``, ``oo``, etc.
    full_dict: dict[str, Any] = {}
    full_dict.update(_SYMPY_NAMES)
    full_dict.update(local_dict)

    return parse_expr(
        expr_str,
        local_dict=full_dict,
        transformations=TRANSFORMATIONS,
        evaluate=False,
    )


# ---------------------------------------------------------------------------
# Pre-processing helpers
# ---------------------------------------------------------------------------

def _preprocess(text: str) -> str:
    """Apply regex-based transformations before sympy parsing."""
    text = _rewrite_derivatives(text)
    text = _rewrite_abs(text)
    text = _rewrite_ln(text)
    return text


def _rewrite_derivatives(text: str) -> str:
    """Convert ``d/dx(expr)`` → ``Derivative(expr, x)``."""
    def _sub(m: re.Match[str]) -> str:
        # Order from digit group or unicode superscript
        order_digit = m.group(1)
        order_unicode = m.group(2)
        var = m.group(3)
        # denominator order (for consistency check)
        _denom_digit = m.group(4)
        _denom_unicode = m.group(5)
        body = m.group(6)

        order = 1
        if order_digit:
            order = int(order_digit)
        elif order_unicode:
            order = _UNICODE_SUPER_MAP.get(order_unicode, 1)

        if order == 1:
            return f"Derivative({body}, {var})"
        return f"Derivative({body}, {var}, {order})"

    return _DERIV_RE.sub(_sub, text)


def _rewrite_abs(text: str) -> str:
    """Convert ``|expr|`` → ``Abs(expr)``."""
    return _ABS_RE.sub(r"Abs(\1)", text)


def _rewrite_ln(text: str) -> str:
    """Convert ``ln(...)`` → ``log(...)`` (sympy uses log for natural log)."""
    return re.sub(r"\bln\b", "log", text)


def _guess_solve_var(expr_str: str) -> str:
    """Heuristic: guess the 'main' variable in an equation expression.

    Picks the first single-letter symbol that isn't a known constant.
    """
    # Find all single-letter identifiers
    candidates = re.findall(r"\b([a-zA-Z])\b", expr_str)
    constants = {"e", "i", "I", "E"}
    for c in candidates:
        if c not in constants:
            return c
    return candidates[0] if candidates else "x"


def _split_plot_args(raw: str) -> list[str]:
    """Split plot argument string respecting parenthesised groups.

    ``sin(x), (x, 0, 10)`` → ``['sin(x)', '(x, 0, 10)']``
    """
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in raw:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return parts


# ---------------------------------------------------------------------------
# Reserved names (prevent accidental assignment)
# ---------------------------------------------------------------------------

_RESERVED_NAMES: frozenset[str] = frozenset({
    # Sympy functions
    "sin", "cos", "tan", "cot", "sec", "csc",
    "asin", "acos", "atan", "atan2",
    "sinh", "cosh", "tanh",
    "exp", "log", "ln", "sqrt", "cbrt",
    "Abs", "sign", "floor", "ceiling",
    "factorial", "gamma", "beta",
    "diff", "integrate", "limit", "series",
    "solve", "dsolve", "simplify", "expand", "factor",
    "plot", "plot3d",
    "Derivative", "Integral", "Limit", "Sum", "Product",
    "Matrix", "det", "inv", "transpose",
    # Constants
    "pi", "E", "I", "oo", "zoo", "nan",
    "true", "false",
    # Special
    "N", "S",
})

# Standard sympy names available in the REPL namespace
_SYMPY_NAMES: dict[str, Any] = {
    "pi": sympy.pi,
    "e": sympy.E,
    "E": sympy.E,
    "I": sympy.I,
    "i": sympy.I,
    "oo": sympy.oo,
    "inf": sympy.oo,
    "nan": sympy.nan,
    "true": sympy.true,
    "false": sympy.false,
    # Functions
    "sin": sympy.sin,
    "cos": sympy.cos,
    "tan": sympy.tan,
    "cot": sympy.cot,
    "sec": sympy.sec,
    "csc": sympy.csc,
    "asin": sympy.asin,
    "acos": sympy.acos,
    "atan": sympy.atan,
    "atan2": sympy.atan2,
    "sinh": sympy.sinh,
    "cosh": sympy.cosh,
    "tanh": sympy.tanh,
    "exp": sympy.exp,
    "log": sympy.log,
    "sqrt": sympy.sqrt,
    "cbrt": sympy.cbrt,
    "Abs": sympy.Abs,
    "sign": sympy.sign,
    "floor": sympy.floor,
    "ceiling": sympy.ceiling,
    "factorial": sympy.factorial,
    "gamma": sympy.gamma,
    "beta": sympy.beta,
    "Derivative": sympy.Derivative,
    "Integral": sympy.Integral,
    "Limit": sympy.Limit,
    "Sum": sympy.Sum,
    "Product": sympy.Product,
    "Matrix": sympy.Matrix,
    "Symbol": sympy.Symbol,
    "symbols": sympy.symbols,
    "Rational": sympy.Rational,
    "binomial": sympy.binomial,
    "Eq": sympy.Eq,
    "solve": sympy.solve,
    "diff": sympy.diff,
    "integrate": sympy.integrate,
    "limit": sympy.limit,
    "series": sympy.series,
    "simplify": sympy.simplify,
    "expand": sympy.expand,
    "factor": sympy.factor,
    "apart": sympy.apart,
    "together": sympy.together,
    "cancel": sympy.cancel,
    "trigsimp": sympy.trigsimp,
    "dsolve": sympy.dsolve,
    "Function": sympy.Function,
}
