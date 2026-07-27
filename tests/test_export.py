"""Tests for session export — LaTeX and Jupyter notebook generation."""

from __future__ import annotations

import tempfile
from pathlib import Path

import sympy

from mathrepl.session.export import export_jupyter, export_latex
from mathrepl.session.state import SessionState


def _make_session_with_history() -> SessionState:
    """Create a session with realistic history for export testing."""
    state = SessionState()
    state.add_history("2*x + 3*x", "5*x")
    state.add_history("d/dx(sin(x))", "cos(x)")
    state.add_history("integrate(x^2, x)", "x**3/3")
    state.add_history("N(pi, 30)", "3.14159265358979323846264338328")
    state.add_history("f(x) := x^2 + 1", "x**2 + 1")
    return state


class TestLatexExport:
    """Tests for LaTeX document export."""

    def test_generates_file(self) -> None:
        state = _make_session_with_history()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "output.tex"
            result = export_latex(state, path)
            assert result.exists()

    def test_has_document_structure(self) -> None:
        state = _make_session_with_history()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "output.tex"
            export_latex(state, path)
            content = path.read_text(encoding="utf-8")
            assert r"\documentclass" in content
            assert r"\begin{document}" in content
            assert r"\end{document}" in content
            assert r"\usepackage{amsmath" in content

    def test_includes_all_entries(self) -> None:
        state = _make_session_with_history()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "output.tex"
            export_latex(state, path)
            content = path.read_text(encoding="utf-8")
            assert "In [1]" in content
            assert "In [5]" in content

    def test_selective_export(self) -> None:
        state = _make_session_with_history()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "output.tex"
            export_latex(state, path, entries=[1, 3])
            content = path.read_text(encoding="utf-8")
            assert "In [1]" in content
            assert "In [3]" in content
            assert "In [2]" not in content

    def test_default_filename(self) -> None:
        state = _make_session_with_history()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use a subdir to avoid polluting cwd
            import os  # noqa: PLC0415
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = export_latex(state)
                assert result.name == "mathrepl_session.tex"
            finally:
                os.chdir(original_cwd)


class TestJupyterExport:
    """Tests for Jupyter notebook export."""

    def test_generates_file(self) -> None:
        state = _make_session_with_history()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "output.ipynb"
            try:
                result = export_jupyter(state, path)
                assert result.exists()
            except ImportError:
                import pytest  # noqa: PLC0415
                pytest.skip("nbformat not installed")

    def test_valid_notebook(self) -> None:
        state = _make_session_with_history()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "output.ipynb"
            try:
                export_jupyter(state, path)
                import nbformat  # noqa: PLC0415
                with open(path, encoding="utf-8") as f:
                    nb = nbformat.read(f, as_version=4)
                # Should have: title cell + setup cell + 5 history cells = 7
                assert len(nb.cells) == 7
            except ImportError:
                import pytest  # noqa: PLC0415
                pytest.skip("nbformat not installed")

    def test_has_setup_cell(self) -> None:
        state = _make_session_with_history()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "output.ipynb"
            try:
                export_jupyter(state, path)
                import nbformat  # noqa: PLC0415
                with open(path, encoding="utf-8") as f:
                    nb = nbformat.read(f, as_version=4)
                # Second cell should be the setup cell with imports
                setup_cell = nb.cells[1]
                assert "from sympy import *" in setup_cell.source
            except ImportError:
                import pytest  # noqa: PLC0415
                pytest.skip("nbformat not installed")
