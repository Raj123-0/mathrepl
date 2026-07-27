"""Main REPL application — wires together parser, engine, session, and rendering.

This is the heart of MathREPL's interactive experience: a persistent
prompt_toolkit session with syntax highlighting, tab-completion,
keyboard shortcuts, and a status toolbar.
"""

from __future__ import annotations

import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style

from mathrepl.engine.evaluator import EvalResult, ResultKind, evaluate
from mathrepl.parser.commands import COMMANDS, format_help
from mathrepl.parser.tokenizer import InputKind, ParseResult, tokenize
from mathrepl.render.highlighting import MathLexer
from mathrepl.render.pretty import (
    get_console,
    render_error,
    render_info,
    render_result,
    render_welcome,
)
from mathrepl.session.state import SessionState
from mathrepl.tui.completer import MathCompleter
from mathrepl.tui.keybindings import create_keybindings
from mathrepl.tui.toolbar import create_toolbar


# ---------------------------------------------------------------------------
# Prompt style
# ---------------------------------------------------------------------------

_PROMPT_STYLE = Style.from_dict({
    "prompt": "bold #06b6d4",       # Cyan input prompt
    "continuation": "#64748b",       # Dim continuation
    "bottom-toolbar": "bg:#1e293b #94a3b8",
})


def run_repl() -> None:
    """Launch the interactive MathREPL session."""
    state = SessionState(precision=15)
    console = get_console()

    # Display welcome banner
    render_welcome()

    # Create prompt_toolkit session
    completer = MathCompleter(state)
    toolbar = create_toolbar(state)

    def _save_callback() -> None:
        from mathrepl.session.persistence import save_session  # noqa: PLC0415
        path = save_session(state)
        render_info(f"  Session saved to {path}")

    kb = create_keybindings(state, callbacks={"save": _save_callback})

    session: PromptSession[str] = PromptSession(
        history=InMemoryHistory(),
        completer=completer,
        lexer=MathLexer(),
        style=_PROMPT_STYLE,
        bottom_toolbar=toolbar,
        key_bindings=kb,
        multiline=False,  # We handle multi-line detection ourselves
        complete_while_typing=True,
        enable_history_search=True,
    )

    # Main REPL loop
    while True:
        try:
            prompt_str = f"In [{state.entry_counter + 1}]: "
            raw_input = session.prompt(prompt_str)
        except KeyboardInterrupt:
            continue
        except EOFError:
            render_info("\nGoodbye!")
            break

        # Handle multi-line: if parens/brackets are unmatched, keep reading
        while _is_incomplete(raw_input):
            try:
                continuation = session.prompt("   ...: ")
                raw_input += "\n" + continuation
            except (KeyboardInterrupt, EOFError):
                break

        # Tokenize
        parsed = tokenize(raw_input)

        # Handle commands
        if parsed.kind == InputKind.COMMAND:
            _handle_command(parsed, state)
            continue

        # Handle plots
        if parsed.kind == InputKind.PLOT:
            _handle_plot(parsed, state)
            continue

        # Evaluate
        result = evaluate(
            parsed,
            variables=state.variables,
            functions=state.functions,
            precision=state.precision,
        )

        # Update state based on result
        _apply_result(result, parsed, state)

        # Record history
        if result.kind not in (ResultKind.EMPTY, ResultKind.ERROR, ResultKind.INFO):
            output_repr = _result_to_repr(result)
            idx = state.add_history(raw_input, output_repr)
            render_result(result, idx)
        elif result.kind == ResultKind.ERROR:
            render_result(result, 0)


def _is_incomplete(text: str) -> bool:
    """Check if the input has unmatched parentheses or brackets."""
    depth_paren = 0
    depth_bracket = 0
    for ch in text:
        if ch == "(":
            depth_paren += 1
        elif ch == ")":
            depth_paren -= 1
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]":
            depth_bracket -= 1
    return depth_paren > 0 or depth_bracket > 0


def _apply_result(
    result: EvalResult,
    parsed: ParseResult,
    state: SessionState,
) -> None:
    """Apply side effects of an evaluation to session state."""
    if result.kind == ResultKind.ASSIGNMENT and result.assign_value is not None:
        state.set_variable(result.assign_target, result.assign_value)

    elif result.kind == ResultKind.FUNC_DEFINITION and result.symbolic is not None:
        state.set_function(
            result.func_name,
            parsed.func_params,
            result.symbolic,
        )

    # Store last result as _
    if result.kind in (ResultKind.SYMBOLIC, ResultKind.NUMERIC) and result.symbolic is not None:
        state.variables["_"] = result.symbolic


def _result_to_repr(result: EvalResult) -> str:
    """Convert an EvalResult to a string for history storage."""
    if result.numeric is not None:
        return str(result.numeric)
    if result.symbolic is not None:
        return str(result.symbolic)
    if result.solutions is not None:
        return str(result.solutions)
    return result.text


# ---------------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------------

def _handle_command(parsed: ParseResult, state: SessionState) -> None:
    """Execute a colon-command."""
    cmd = parsed.command
    args = parsed.command_args

    match cmd:
        case "help" | "h" | "?":
            target = args[0] if args else None
            render_info(format_help(target))

        case "precision" | "prec":
            if args:
                try:
                    new_prec = int(args[0])
                    state.precision = new_prec
                    render_info(f"  Precision set to {new_prec} digits.")
                except ValueError:
                    render_error(f"Invalid precision: {args[0]}")
            else:
                render_info(f"  Current precision: {state.precision} digits.")

        case "undo" | "u":
            if state.undo():
                render_info("  ↶ Undone.")
            else:
                render_info("  Nothing to undo.")

        case "history" | "hist":
            n = int(args[0]) if args else None
            entries = state.get_history(n)
            if not entries:
                render_info("  No history yet.")
            else:
                for entry in entries:
                    render_info(f"  [{entry.index}] {entry.input_str}")

        case "vars" | "v" | "variables":
            if not state.variables:
                render_info("  No variables defined.")
            else:
                import sympy  # noqa: PLC0415
                for name, val in state.variables.items():
                    render_info(f"  {name} = {sympy.pretty(val, use_unicode=True)}")

        case "funcs" | "functions":
            if not state.functions:
                render_info("  No functions defined.")
            else:
                import sympy  # noqa: PLC0415
                for name, (params, body) in state.functions.items():
                    params_str = ", ".join(str(p) for p in params)
                    body_str = sympy.pretty(body, use_unicode=True)
                    render_info(f"  {name}({params_str}) := {body_str}")

        case "clear" | "reset":
            state.clear()
            render_info("  Session cleared.")

        case "save" | "s":
            from mathrepl.session.persistence import save_session  # noqa: PLC0415
            path_arg = args[0] if args else None
            path = save_session(state, path_arg)
            render_info(f"  Session saved to {path}")

        case "load" | "l":
            if not args:
                render_error("Usage: :load <filepath>")
                return
            from mathrepl.session.persistence import load_session  # noqa: PLC0415
            try:
                loaded = load_session(args[0])
                # Replace state contents
                state.variables = loaded.variables
                state.functions = loaded.functions
                state.history = loaded.history
                state._entry_counter = loaded.entry_counter
                state.precision = loaded.precision
                render_info(f"  Session loaded from {args[0]}")
            except (FileNotFoundError, ValueError) as exc:
                render_error(str(exc))

        case "export" | "ex":
            _handle_export(args, state)

        case "units":
            if args:
                render_info(f"  Units mode: {args[0]} (not yet implemented)")
            else:
                render_info("  Units mode: use :units on/off")

        case "quit" | "q" | "exit":
            render_info("Goodbye!")
            sys.exit(0)

        case _:
            render_error(f"Unknown command: :{cmd}. Type :help for available commands.")


def _handle_export(args: list[str], state: SessionState) -> None:
    """Handle the :export command."""
    if not args:
        render_error("Usage: :export <latex|jupyter> [filepath]")
        return

    fmt = args[0].lower()
    path = args[1] if len(args) > 1 else None

    if fmt == "latex":
        from mathrepl.session.export import export_latex  # noqa: PLC0415
        filepath = export_latex(state, path)
        render_info(f"  Exported to LaTeX: {filepath}")
    elif fmt in ("jupyter", "ipynb", "notebook"):
        from mathrepl.session.export import export_jupyter  # noqa: PLC0415
        try:
            filepath = export_jupyter(state, path)
            render_info(f"  Exported to Jupyter: {filepath}")
        except ImportError as exc:
            render_error(str(exc))
    else:
        render_error(f"Unknown export format: {fmt}. Use 'latex' or 'jupyter'.")


def _handle_plot(parsed: ParseResult, state: SessionState) -> None:
    """Handle a plot command."""
    from mathrepl.render.plots import render_plot  # noqa: PLC0415

    result = render_plot(
        parsed.plot_args,
        variables=state.variables,
        functions=state.functions,
        plot_type=parsed.command,
    )
    if result:
        render_info(f"  {result}")
