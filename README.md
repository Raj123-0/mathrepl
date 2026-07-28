# MathREPL

> A terminal-based, interactive math notebook — a persistent REPL where you type
> mathematical expressions and get instant symbolic simplification, arbitrary-precision
> numeric evaluation, and inline plots.

<p align="center">
  <em>Like a lightweight, scriptable Mathematica notebook that lives in your terminal.</em>
</p>

---

##  Features

- **Natural math input** — write `2x + 3x`, `d/dx(sin(x))`, `x^2` instead of
  verbose Python syntax
- **Symbolic simplification** — every expression is simplified automatically;
  numeric approximation only on explicit request (`N(pi, 50)` or trailing `=`)
- **Arbitrary precision** — set working precision with `:precision 50` and get
  50-digit results, not silent double-precision rounding
- **Session state** — define variables (`a = 42`) and functions (`f(x) := x^2 + 1`)
  that persist across the session
- **Equation solving** — write `x^2 - 1 == 0` and get the solutions
- **Calculus** — differentiate (`d/dx(...)`), integrate, limits, series expansion,
  ODE solving — all with natural syntax
- **Inline plots** — `plot(sin(x), (x, 0, 10))` renders directly in your terminal
  (Kitty/iTerm2) or opens a matplotlib window
- **Session persistence** — `:save` / `:load` your session and pick up tomorrow
  where you left off
- **Export** — `:export latex` or `:export jupyter` to turn your terminal session
  into a shareable document
- **Syntax highlighting** — math keywords, constants, and operators are
  colour-coded as you type
- **Tab completion** — complete function names, variables, and commands
- **Physical units** — `3 * meter / second` type-checks and converts (via
  `sympy.physics.units`)
- **Plugin system** — define custom constants and startup expressions in
  `~/.mathreplrc`

##  Installation

```bash
# Clone and install in editable mode with all extras
git clone <repo-url>
cd mathrepl
pip install -e ".[all]"

# Or with just the core (no plots/export):
pip install -e .
```

### Optional dependencies

| Extra | Packages | What it enables |
|-------|----------|-----------------|
| `plots` | matplotlib | `plot()` / `plot3d()` commands |
| `export` | nbformat | `:export jupyter` command |
| `all` | everything above | Full feature set |

##  Quick Start

```
$ mathrepl

╔══════════════════════════════════════════════╗
║           MathREPL v0.1.0                    ║
║   Interactive Symbolic Math Notebook         ║
╚══════════════════════════════════════════════╝

In [1]: 2x + 3x
Out[1]: 5⋅x

In [2]: d/dx(sin(x))
Out[2]: cos(x)

In [3]: f(x) := x^2 + 1
  f(…) defined: x² + 1

In [4]: f(3)
Out[4]: 10

In [5]: integrate(x^2, x)
         3
        x
Out[5]: ──
        3

In [6]: x^2 - 1 == 0
  x₍₁₎ = -1
  x₍₂₎ = 1

In [7]: :precision 50
  Precision set to 50 digits.

In [8]: N(pi)
Out[8]: 3.1415926535897932384626433832795028841971693993751

In [9]: :save my_work
  Session saved to my_work.mathrepl

In [10]: :export latex
  Exported to LaTeX: mathrepl_session.tex
```

##  Commands

| Command | Description |
|---------|-------------|
| `:help` | Show help / cheatsheet |
| `:precision N` | Set working precision to N digits |
| `:undo` | Roll back last state change |
| `:history` | Show numbered input history |
| `:vars` | List defined variables |
| `:funcs` | List defined functions |
| `:clear` | Reset session state |
| `:save [path]` | Save session to file |
| `:load <path>` | Load session from file |
| `:export latex [path]` | Export to LaTeX |
| `:export jupyter [path]` | Export to Jupyter notebook |
| `:quit` | Exit |

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Quick-save session |
| `Ctrl+U` | Undo last entry |
| `Ctrl+L` | Clear screen |
| `Ctrl+D` | Exit |
| `Tab` | Autocomplete |
| `↑` / `↓` | Navigate history |

##  Why Not Just Use a Jupyter Notebook?

This is a fair question, and the honest answer is: **Jupyter is often the better
choice.** Here's when each tool wins:

### MathREPL wins when…

- **You want something instant.** Opening a terminal and typing `mathrepl` is
  faster than launching a Jupyter server, opening a browser, creating a notebook,
  and importing sympy.
- **You're already in a terminal workflow.** If you're SSH'd into a server, in
  `tmux`, or using a tiling window manager, MathREPL fits naturally.
- **You want a scratchpad.** Quick "what's the derivative of this?" questions
  don't need a full notebook environment.
- **Precision matters.** Jupyter notebooks silently use hardware floats by
  default; MathREPL gives you arbitrary precision with a single command.
- **You want deterministic state.** MathREPL's session is a linear history with
  undo — no "did I run cell 3 before cell 7?" confusion.

### Jupyter wins when…

- **You need rich output.** LaTeX rendering, interactive widgets, inline images
  with pan/zoom — a browser environment is simply more capable.
- **You're doing data science.** Pandas DataFrames, Plotly charts, and ML
  model outputs are Jupyter's home turf.
- **You need collaboration.** JupyterHub, Google Colab, and nbviewer make
  sharing effortless.
- **You're writing a narrative.** Markdown cells, section headers, and
  interspersed code make Jupyter a better "literate programming" tool.
- **You need the Python ecosystem.** MathREPL is a math-focused tool, not a
  general Python REPL. If you need `import pandas`, use Jupyter or IPython.

**Bottom line:** MathREPL is for people who leave a terminal open all day and
want a fast, focused math scratchpad with symbolic intelligence. It's not a
Jupyter replacement — it's a Jupyter *complement*.

##  Architecture

```
src/mathrepl/
├── parser/              # Input tokenization and classification
│   ├── tokenizer.py     # Implicit mult, d/dx, :=, N(), == detection
│   ├── transformer.py   # AST post-processing and simplification
│   └── commands.py      # :command registry and help text
├── engine/              # Evaluation and computation
│   ├── evaluator.py     # Core eval pipeline
│   ├── calculus.py      # diff, integrate, limit, series
│   ├── algebra.py       # solve, dsolve, matrix ops
│   ├── numeric.py       # Arbitrary precision via mpmath
│   └── units.py         # Physical units
├── session/             # State management
│   ├── state.py         # SessionState: vars, funcs, history, undo
│   ├── persistence.py   # Save/load .mathrepl files
│   └── export.py        # LaTeX and Jupyter export
├── render/              # Terminal output
│   ├── pretty.py        # Unicode math rendering + Rich theming
│   ├── plots.py         # Matplotlib + terminal image protocol
│   └── highlighting.py  # Syntax highlighting lexer
├── tui/                 # Interactive shell
│   ├── app.py           # Main REPL loop (prompt_toolkit)
│   ├── completer.py     # Tab completion
│   ├── keybindings.py   # Keyboard shortcuts
│   └── toolbar.py       # Bottom status bar
└── config/              # Configuration
    └── loader.py        # ~/.mathreplrc loading
```

##  Running Tests

```bash
python -m pytest tests/ -v
```

##  Future Work (Stretch Goals)

- **Natural language input** — "integrate x squared from 0 to 1" parsed via a
  small grammar (no LLM needed)
- **Step-by-step mode** — show intermediate simplification/solving steps
- **OEIS integration** — `:oeis <sequence>` to look up computed values against
  the Online Encyclopedia of Integer Sequences
- **Multi-user shared sessions** — two terminals, same session, over a local socket

##  License

MIT
