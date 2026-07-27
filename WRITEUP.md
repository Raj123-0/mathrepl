# MathREPL — Design Write-Up

This document covers the non-trivial engineering challenges encountered while
building MathREPL: a terminal-based interactive math notebook with symbolic
computation, arbitrary precision, and inline rendering.

---

## 1. Parsing: The Implicit Multiplication Problem

### The ambiguity

The single trickiest parsing problem in MathREPL is **implicit multiplication**.
Users expect to write `2x` and have it mean `2*x`, `xy` as `x*y`, and `3sin(x)`
as `3*sin(x)`. This is natural mathematical notation, but it creates genuine
ambiguity:

| Input | Intended meaning | Ambiguous alternative |
|-------|------------------|-----------------------|
| `x(2)` | Function call `x(2)` | Multiplication `x * 2` |
| `e(x)` | Function call on `e` | Euler's number × `x` |
| `xy(z)` | `x * y(z)`? `xy(z)` call? | Both are valid readings |

### Resolution strategy

We use a layered approach:

1. **Reserved names**: A curated set of names (`sin`, `cos`, `pi`, `e`, etc.)
   are never treated as multiplication targets. `e(x)` is always `e * x` because
   `e` is a known constant, but `f(x)` is a function call because `f` is not
   reserved.

2. **Sympy's `implicit_multiplication_application` transformation**: This handles
   the common cases (`2x`, `3sin(x)`) at the token level before full parsing.

3. **Regex pre-processing**: Before handing to sympy, we rewrite patterns that
   sympy's transformer doesn't handle — derivative notation (`d/dx(...)`) and
   assignment syntax (`:=`).

4. **Post-parse function resolution**: After parsing, we walk the AST looking
   for `AppliedUndef` nodes matching user-defined functions and substitute their
   bodies with appropriate argument bindings.

### What still breaks

The approach is not perfect. `x(2+3)` will be parsed as a function call on `x`,
not as `x * 5`. In a pure math context, the user likely means multiplication,
but in a CAS that supports first-class functions, the call interpretation is
defensible. We err on the side of function-call semantics for unrecognised
names, which matches both Python and Mathematica behaviour.

---

## 2. Precision Handling

### The problem

Python floats are IEEE 754 double-precision: ~15–17 significant digits. Sympy
operates symbolically (exact), but the moment you call `.evalf()`, you enter the
world of finite precision. The question is: **whose precision?**

### Our approach

MathREPL manages precision through a single global value in `mpmath.mp.dps`
(decimal places). This value is:

- Set once at session start (default: 15)
- Changed via `:precision N`
- Stored in session state (survives save/load)
- Passed explicitly to every `evalf(n=...)` call

### Pitfalls we avoid

1. **Silent float contamination**: If the user writes `0.1` in an expression,
   sympy creates a Python `float`, which is then a 64-bit double — potentially
   ruining a 100-digit computation. Sympy's `parse_expr` with
   `standard_transformations` converts numeric literals to sympy `Number` objects,
   avoiding this trap.

2. **Mixing precisions**: If a user computes `a = N(pi, 50)` and then uses `a`
   in a later expression evaluated at 100 digits, the `a` value is only 50-digit
   precise. We store symbolic forms (not evaluated forms) in session variables,
   so `a = pi` stores `sympy.pi`, not a float.

3. **Guard digits**: When validating precision (our regression tests compare
   against known values of π and e), we compute with `digits + 5` guard digits
   to account for rounding in the final digit.

### Validation

The test suite includes regression tests that validate π, e, and √2 at 15, 50,
and 100 digit precision against hardcoded known values. This catches any
accidental precision degradation.

---

## 3. Terminal Rendering

### Unicode math

Sympy's `pretty()` function produces surprisingly good Unicode renderings of
mathematical expressions:

```
⌠
⎮  2
⎮ x  dx
⌡

    3
   x
   ──
   3
```

This works well in most modern terminals. We force `use_unicode=True` because
sympy's auto-detection sometimes falls back to ASCII unnecessarily.

### Colour

We use Rich's `Console` with a custom theme to colour-code output:
- **Cyan** for input prompts (`In [n]:`)
- **Green** for output labels (`Out[n]:`)
- **Yellow** for numeric results
- **Magenta** for assignments
- **Red** for errors

### Plots

Terminal plot rendering is genuinely difficult on Windows. The approach:

1. **Kitty/iTerm2 graphics protocol**: If the terminal supports it (detected via
   `TERM_PROGRAM` env var), we encode the matplotlib figure as PNG, base64 it,
   and write it using the Kitty escape sequence. This renders inline.

2. **Matplotlib window**: If no inline protocol is available, `plt.show()` opens
   a native window. This works on Windows, macOS, and Linux with a display server.

3. **File fallback**: As a last resort, save to a temp PNG and print the path.

On Windows (the primary dev platform), option 2 is the typical path. Windows
Terminal has experimental sixel support that may improve inline rendering in the
future.

---

## 4. Session Serialisation

### The challenge

Sympy expressions are complex Python objects with rich type hierarchies. We need
lossless round-tripping: save a session, close the REPL, reopen, load, and have
every expression be *exactly* the same object.

### Solution: `srepr()`

Sympy's `srepr()` function produces a string that, when `eval()`'d with the
right namespace, reconstructs the exact expression:

```python
>>> srepr(pi**2 + sqrt(2))
"Add(Pow(pi, Integer(2)), Pow(Integer(2), Rational(1, 2)))"
```

This is verbose but **lossless** — unlike `str()` (which loses type information)
or `latex()` (which is for display, not reconstruction).

We store these `srepr()` strings in a JSON file with a version key for forward
compatibility. On load, we use `sympy.sympify()` to reconstruct — this calls
`eval()` internally, which is safe because the file is user-controlled (local
disk, not network input).

### History

History entries store the raw input string and the `str()` output representation.
These are for display replay, not symbolic reconstruction — if you need the
exact symbolic value, that's in the variables/functions dict.

---

## 5. Startup Performance

### Target: <300ms cold start

Heavy imports destroy REPL startup time. `import matplotlib` alone takes ~500ms.
`import sympy` takes ~200ms (unavoidable — it's our core dependency).

### Strategy: lazy imports

- `matplotlib`: Only imported when the first `plot()` command is executed
- `nbformat`: Only imported when `:export jupyter` is called
- `numpy`: Only imported for plot data generation
- `pint`: Only imported when units mode is enabled

The core startup path imports only: `sympy`, `mpmath`, `prompt_toolkit`, `rich`,
and our own modules. This keeps cold start well under the 300ms target.

---

## 6. Extensibility: `~/.mathreplrc`

The config file uses Python syntax parsed via `ast.literal_eval()` for safety.
This means users can define dicts, lists, ints, and strings — but not arbitrary
code. The file is read at startup and its contents (custom constants, default
precision, startup expressions) are applied to the session state before the REPL
prompt appears.

This is intentionally limited compared to a full plugin system (which would need
sandboxing, dependency management, etc.). For v0.1, "define some constants and
set your preferred precision" covers the 90% use case.
