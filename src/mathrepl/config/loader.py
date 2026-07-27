"""Configuration loader — reads ``~/.mathreplrc`` at startup.

The config file is a Python-syntax file that can define:
- Custom constants
- Default precision
- Startup expressions
- Color theme overrides
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import sympy
from sympy import Basic


DEFAULT_CONFIG_PATH = Path.home() / ".mathreplrc"


def load_config(
    path: Path | None = None,
) -> dict[str, Any]:
    """Load configuration from a ``.mathreplrc`` file.

    Parameters
    ----------
    path:
        Path to the config file.  Defaults to ``~/.mathreplrc``.

    Returns
    -------
    dict
        Parsed configuration with keys:
        - ``"constants"``: dict of name → sympy expression
        - ``"precision"``: int
        - ``"startup"``: list of expression strings to evaluate
        - ``"units"``: bool (whether to enable units by default)
    """
    config: dict[str, Any] = {
        "constants": {},
        "precision": 15,
        "startup": [],
        "units": False,
    }

    filepath = path or DEFAULT_CONFIG_PATH
    if not filepath.exists():
        return config

    try:
        text = filepath.read_text(encoding="utf-8")
        # Parse as Python to extract assignments safely
        tree = ast.parse(text, filename=str(filepath))

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name):
                    name = target.id
                    value = ast.literal_eval(node.value)

                    if name == "constants" and isinstance(value, dict):
                        # Convert numeric values to sympy
                        config["constants"] = {
                            k: sympy.sympify(v) for k, v in value.items()
                        }
                    elif name == "precision" and isinstance(value, int):
                        config["precision"] = value
                    elif name == "startup" and isinstance(value, list):
                        config["startup"] = value
                    elif name == "units" and isinstance(value, bool):
                        config["units"] = value

    except Exception as exc:  # noqa: BLE001
        # Don't crash on bad config — just warn
        import warnings  # noqa: PLC0415
        warnings.warn(f"Error loading {filepath}: {exc}", stacklevel=2)

    return config


def apply_config(
    config: dict[str, Any],
    variables: dict[str, Basic],
    precision_setter: Any = None,
) -> None:
    """Apply loaded config to the session state.

    Parameters
    ----------
    config:
        The config dict from :func:`load_config`.
    variables:
        The session's variable dict to populate with constants.
    precision_setter:
        A callable to set precision (e.g. ``session.precision = ...``).
    """
    # Apply custom constants
    for name, value in config.get("constants", {}).items():
        variables[name] = value

    # Apply precision
    if precision_setter and "precision" in config:
        precision_setter(config["precision"])
