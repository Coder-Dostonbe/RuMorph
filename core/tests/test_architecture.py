"""tilsim_core must run under Pyodide in the app and in a Python Worker, so it
may import only the standard library and its own modules."""

import ast
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "tilsim_core"
STDLIB = set(sys.stdlib_module_names)
# Standard-library modules that Pyodide does not ship or that need the network or threads.
FORBIDDEN_STDLIB = {"socket", "ssl", "subprocess", "multiprocessing", "threading", "asyncio",
                    "urllib", "http", "sqlite3", "tkinter", "ctypes"}


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_package_imports_only_the_standard_library():
    offenders = {}
    for path in PACKAGE.rglob("*.py"):
        bad = {r for r in imported_roots(path) if r != "tilsim_core" and (r not in STDLIB or r in FORBIDDEN_STDLIB)}
        if bad:
            offenders[str(path.relative_to(PACKAGE))] = sorted(bad)
    assert offenders == {}


def test_package_has_files():
    assert list(PACKAGE.rglob("*.py"))
