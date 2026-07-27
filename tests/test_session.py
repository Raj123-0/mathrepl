"""Tests for session state — variables, functions, history, undo, and round-tripping."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import sympy
from sympy import Symbol

from mathrepl.session.persistence import load_session, save_session
from mathrepl.session.state import SessionState


class TestSessionVariables:
    """Tests for variable management."""

    def test_set_variable(self, session: SessionState) -> None:
        session.set_variable("a", sympy.Integer(42))
        assert session.variables["a"] == 42

    def test_variable_overwrite(self, session: SessionState) -> None:
        session.set_variable("a", sympy.Integer(1))
        session.set_variable("a", sympy.Integer(2))
        assert session.variables["a"] == 2

    def test_variable_count(self, populated_session: SessionState) -> None:
        assert len(populated_session.variables) == 2


class TestSessionFunctions:
    """Tests for function definitions."""

    def test_define_function(self, session: SessionState) -> None:
        x = Symbol("x")
        session.set_function("f", ["x"], x**2 + 1)  # type: ignore
        assert "f" in session.functions
        params, body = session.functions["f"]
        assert len(params) == 1
        assert str(params[0]) == "x"

    def test_function_count(self, populated_session: SessionState) -> None:
        assert len(populated_session.functions) == 2


class TestSessionHistory:
    """Tests for history recording."""

    def test_add_history(self, session: SessionState) -> None:
        idx = session.add_history("2 + 2", "4")
        assert idx == 1
        assert len(session.history) == 1
        assert session.history[0].input_str == "2 + 2"

    def test_history_ordering(self, session: SessionState) -> None:
        session.add_history("first", "1")
        session.add_history("second", "2")
        session.add_history("third", "3")
        assert [e.input_str for e in session.history] == ["first", "second", "third"]

    def test_get_history_last_n(self, populated_session: SessionState) -> None:
        entries = populated_session.get_history(last_n=2)
        assert len(entries) == 2
        assert entries[0].input_str == "b = 1/3"


class TestSessionUndo:
    """Tests for the undo mechanism."""

    def test_undo_variable(self, session: SessionState) -> None:
        session.set_variable("a", sympy.Integer(1))
        assert "a" in session.variables
        result = session.undo()
        assert result is True
        assert "a" not in session.variables

    def test_undo_empty_stack(self, session: SessionState) -> None:
        result = session.undo()
        assert result is False

    def test_undo_precision(self, session: SessionState) -> None:
        original = session.precision
        session.precision = 50
        assert session.precision == 50
        session.undo()
        assert session.precision == original


class TestSessionPersistence:
    """Tests for save/load round-tripping."""

    def test_save_and_load_variables(self, populated_session: SessionState) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.mathrepl"
            save_session(populated_session, path)

            loaded = load_session(path)
            assert loaded.variables["a"] == populated_session.variables["a"]
            assert loaded.variables["b"] == populated_session.variables["b"]

    def test_save_and_load_functions(self, populated_session: SessionState) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.mathrepl"
            save_session(populated_session, path)

            loaded = load_session(path)
            assert "f" in loaded.functions
            assert "g" in loaded.functions

    def test_save_and_load_history(self, populated_session: SessionState) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.mathrepl"
            save_session(populated_session, path)

            loaded = load_session(path)
            assert len(loaded.history) == len(populated_session.history)
            for orig, loaded_entry in zip(populated_session.history, loaded.history):
                assert orig.input_str == loaded_entry.input_str
                assert orig.output_repr == loaded_entry.output_repr

    def test_save_and_load_precision(self) -> None:
        state = SessionState(precision=42)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.mathrepl"
            save_session(state, path)

            loaded = load_session(path)
            assert loaded.precision == 42

    def test_load_nonexistent_file(self) -> None:
        import pytest  # noqa: PLC0415
        with pytest.raises(FileNotFoundError):
            load_session("/nonexistent/path.mathrepl")

    def test_load_invalid_json(self) -> None:
        import pytest  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.mathrepl"
            path.write_text("not json", encoding="utf-8")
            with pytest.raises(ValueError, match="Invalid session"):
                load_session(path)

    def test_load_missing_version(self) -> None:
        import pytest  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nover.mathrepl"
            path.write_text("{}", encoding="utf-8")
            with pytest.raises(ValueError, match="version"):
                load_session(path)


class TestSessionClear:
    """Tests for session clearing."""

    def test_clear(self, populated_session: SessionState) -> None:
        populated_session.clear()
        assert len(populated_session.variables) == 0
        assert len(populated_session.functions) == 0
        assert len(populated_session.history) == 0

    def test_clear_undo(self, populated_session: SessionState) -> None:
        """Clearing should be undoable."""
        populated_session.clear()
        populated_session.undo()
        assert len(populated_session.variables) == 2
