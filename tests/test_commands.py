"""Tests for colon-commands."""

from __future__ import annotations

from mathrepl.parser.commands import COMMANDS, format_help
from mathrepl.parser.tokenizer import InputKind, tokenize


class TestCommandParsing:
    """Tests that commands are parsed correctly."""

    def test_help_command(self) -> None:
        result = tokenize(":help")
        assert result.kind == InputKind.COMMAND
        assert result.command == "help"

    def test_help_alias(self) -> None:
        result = tokenize(":h")
        assert result.kind == InputKind.COMMAND
        assert result.command == "h"

    def test_precision_with_arg(self) -> None:
        result = tokenize(":precision 50")
        assert result.command == "precision"
        assert result.command_args == ["50"]

    def test_save_with_path(self) -> None:
        result = tokenize(":save my_session.mathrepl")
        assert result.command == "save"
        assert result.command_args == ["my_session.mathrepl"]

    def test_export_with_format(self) -> None:
        result = tokenize(":export latex output.tex")
        assert result.command == "export"
        assert result.command_args == ["latex", "output.tex"]

    def test_quit(self) -> None:
        result = tokenize(":quit")
        assert result.command == "quit"

    def test_quit_alias(self) -> None:
        result = tokenize(":q")
        assert result.command == "q"


class TestCommandRegistry:
    """Tests that all commands are registered."""

    def test_all_commands_registered(self) -> None:
        expected = {"help", "precision", "undo", "history", "vars", "funcs",
                    "clear", "save", "load", "export", "quit", "units"}
        for cmd in expected:
            assert cmd in COMMANDS, f"Command '{cmd}' not registered"

    def test_aliases_registered(self) -> None:
        assert "h" in COMMANDS
        assert "q" in COMMANDS
        assert "prec" in COMMANDS

    def test_help_text_generation(self) -> None:
        text = format_help()
        assert "MathREPL Commands" in text
        assert ":help" in text
        assert ":quit" in text

    def test_specific_help(self) -> None:
        text = format_help("help")
        assert ":help" in text
        assert "Show" in text
