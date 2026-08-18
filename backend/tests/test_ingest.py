"""Tests for the M2 tree-sitter ingest module.

All tests use real tree-sitter parsing against fixture files —
no mocks or monkeypatching.
"""
from pathlib import Path

import pytest

from codegraph.ingest.models import Symbol
from codegraph.ingest.parsers import parse_python, parse_typescript
from codegraph.ingest.walker import ingest_repo

FIXTURES = Path(__file__).parent / "fixtures" / "sample_repo"
SAMPLE_PY = FIXTURES / "sample.py"
UTILS_TS = FIXTURES / "utils.ts"


# ---------------------------------------------------------------------------
# Python parser tests
# ---------------------------------------------------------------------------


def _py_symbols() -> list[Symbol]:
    return parse_python(SAMPLE_PY)


def test_python_classes():
    syms = _py_symbols()
    names = [(s.kind, s.name) for s in syms]
    assert ("Class", "Greeter") in names


def test_python_methods():
    syms = _py_symbols()
    method = next((s for s in syms if s.kind == "Method" and s.name == "hello"), None)
    assert method is not None
    assert method.parent == "Greeter"


def test_python_functions():
    syms = _py_symbols()
    names = [(s.kind, s.name) for s in syms]
    assert ("Function", "standalone") in names


def test_line_spans():
    syms = _py_symbols()
    greeter = next(s for s in syms if s.kind == "Class" and s.name == "Greeter")
    standalone = next(s for s in syms if s.kind == "Function" and s.name == "standalone")
    assert greeter.start_line == 1
    assert standalone.start_line == 5


# ---------------------------------------------------------------------------
# TypeScript/JS parser tests
# ---------------------------------------------------------------------------


def _ts_symbols() -> list[Symbol]:
    return parse_typescript(UTILS_TS)


def test_typescript_classes():
    syms = _ts_symbols()
    names = [(s.kind, s.name) for s in syms]
    assert ("Class", "Calculator") in names


def test_typescript_methods():
    syms = _ts_symbols()
    method = next((s for s in syms if s.kind == "Method" and s.name == "add"), None)
    assert method is not None
    assert method.parent == "Calculator"


def test_typescript_functions():
    syms = _ts_symbols()
    names = [(s.kind, s.name) for s in syms]
    assert ("Function", "greet") in names


# ---------------------------------------------------------------------------
# Walker (ingest_repo) tests
# ---------------------------------------------------------------------------


def test_ingest_repo_file_symbols():
    syms = ingest_repo(FIXTURES)
    file_names = {s.name for s in syms if s.kind == "File"}
    # Path separators vary by OS; normalise
    normalised = {n.replace("\\", "/") for n in file_names}
    assert "sample.py" in normalised
    assert "utils.ts" in normalised


def test_ingest_repo_skips_hidden():
    syms = ingest_repo(FIXTURES)
    # No symbol should come from .hidden/secret.py
    for s in syms:
        assert ".hidden" not in s.file.replace("\\", "/"), (
            f"Expected .hidden to be skipped but found: {s.file}"
        )


def test_ingest_repo_includes_children():
    """Walker results should include child symbols (not just File entries)."""
    syms = ingest_repo(FIXTURES)
    kinds = {s.kind for s in syms}
    assert "Class" in kinds
    assert "Function" in kinds
    assert "Method" in kinds
