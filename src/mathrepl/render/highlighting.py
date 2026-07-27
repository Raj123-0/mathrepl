"""Syntax highlighting lexer for MathREPL input.

Provides a custom ``prompt_toolkit`` ``Lexer`` that highlights math
keywords, operators, numbers, and colon-commands with distinct styles.
"""

from __future__ import annotations

import re
from typing import Callable

from prompt_toolkit.document import Document
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.formatted_text import StyleAndTextTuples


# ---------------------------------------------------------------------------
# Token types → prompt_toolkit style strings
# ---------------------------------------------------------------------------

STYLES = {
    "keyword": "bold #5eead4",       # Teal — math functions
    "constant": "bold #f0abfc",      # Purple — pi, e, oo
    "number": "#fbbf24",             # Amber — numeric literals
    "operator": "bold #f87171",      # Red — +, -, *, /
    "paren": "bold #60a5fa",         # Blue — parentheses
    "command": "bold #22d3ee",       # Cyan — :commands
    "assign": "bold #a78bfa",        # Violet — := and =
    "text": "",                       # Default
}

# Math function keywords
_KEYWORDS = frozenset({
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
    "N", "Eq",
    "binomial", "apart", "together", "cancel", "trigsimp",
})

# Constants
_CONSTANTS = frozenset({
    "pi", "e", "E", "I", "i", "oo", "inf", "nan",
    "true", "false",
})

# Tokenisation pattern
_TOKEN_RE = re.compile(
    r"(:[a-zA-Z_]\w*)"           # :commands
    r"|(:=)"                      # := assignment
    r"|(==|!=|<=|>=)"             # comparison operators
    r"|([+\-*/^!%])"             # single-char operators
    r"|([()]|\[|\])"             # parentheses/brackets
    r"|(\d+\.?\d*(?:[eE][+-]?\d+)?)"  # numbers
    r"|([a-zA-Z_]\w*)"           # identifiers
    r"|(\s+)"                    # whitespace
    r"|(.)"                       # anything else
)


class MathLexer(Lexer):
    """A prompt_toolkit Lexer for MathREPL input syntax highlighting."""

    def lex_document(self, document: Document) -> Callable[[int], StyleAndTextTuples]:
        """Return a callable that, given a line number, returns styled tokens."""
        lines = document.lines

        def get_line(lineno: int) -> StyleAndTextTuples:
            if lineno >= len(lines):
                return []

            line = lines[lineno]
            result: StyleAndTextTuples = []

            for m in _TOKEN_RE.finditer(line):
                command = m.group(1)
                assign_op = m.group(2)
                comparison = m.group(3)
                operator = m.group(4)
                paren = m.group(5)
                number = m.group(6)
                identifier = m.group(7)
                whitespace = m.group(8)
                other = m.group(9)

                if command:
                    result.append((STYLES["command"], command))
                elif assign_op:
                    result.append((STYLES["assign"], assign_op))
                elif comparison:
                    result.append((STYLES["operator"], comparison))
                elif operator:
                    result.append((STYLES["operator"], operator))
                elif paren:
                    result.append((STYLES["paren"], paren))
                elif number:
                    result.append((STYLES["number"], number))
                elif identifier:
                    if identifier in _KEYWORDS:
                        result.append((STYLES["keyword"], identifier))
                    elif identifier in _CONSTANTS:
                        result.append((STYLES["constant"], identifier))
                    else:
                        result.append((STYLES["text"], identifier))
                elif whitespace:
                    result.append(("", whitespace))
                elif other:
                    result.append((STYLES["text"], other))

            return result

        return get_line
