from __future__ import annotations

from pathlib import Path

from .models import Symbol
from .parsers import parse_python, parse_typescript

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".tox", "dist", "build"}

_PY_EXTS = {".py"}
_TS_EXTS = {".ts", ".tsx", ".js", ".jsx"}


def ingest_repo(root: str | Path) -> list[Symbol]:
    """Walk *root*, parse every Python and JS/TS file, return flat list of symbols.

    Each file is preceded by a ``Symbol(kind="File", ...)`` entry, followed by
    the symbols extracted from that file (classes, functions, methods).
    """
    root = Path(root).resolve()
    results: list[Symbol] = []

    for path in sorted(root.rglob("*")):
        # Skip hidden directories and known noise dirs
        if any(part.startswith(".") or part in _SKIP_DIRS for part in path.parts[len(root.parts):]):
            continue
        if not path.is_file():
            continue

        ext = path.suffix.lower()
        if ext not in _PY_EXTS and ext not in _TS_EXTS:
            continue

        rel = path.relative_to(root)
        line_count = _count_lines(path)

        # File-level symbol
        results.append(Symbol(
            kind="File",
            name=str(rel),
            file=str(path),
            start_line=1,
            end_line=line_count,
        ))

        if ext in _PY_EXTS:
            results.extend(parse_python(path))
        else:
            results.extend(parse_typescript(path))

    return results


def _count_lines(path: Path) -> int:
    try:
        return path.read_bytes().count(b"\n") + 1
    except OSError:
        return 0
