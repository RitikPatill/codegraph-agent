from __future__ import annotations

from pathlib import Path

import tree_sitter_python
import tree_sitter_javascript
from tree_sitter import Language, Parser

from .models import Symbol

_PY_LANGUAGE = Language(tree_sitter_python.language())
_JS_LANGUAGE = Language(tree_sitter_javascript.language())

_MAX_FILE_SIZE = 1_000_000  # 1 MB


def _is_parseable(path: Path) -> bool:
    """Return False for binary or oversized files."""
    if path.stat().st_size > _MAX_FILE_SIZE:
        return False
    try:
        path.read_bytes()[:512].decode("utf-8")
        return True
    except (UnicodeDecodeError, OSError):
        return False


def _node_text(node) -> str:
    return node.text.decode("utf-8", errors="replace") if node and node.text else ""


def parse_python(path: Path) -> list[Symbol]:
    """Parse a Python file and return Class, Function, and Method symbols."""
    if not _is_parseable(path):
        return []

    source = path.read_bytes()
    parser = Parser(_PY_LANGUAGE)
    tree = parser.parse(source)
    abs_path = str(path.resolve())

    symbols: list[Symbol] = []
    _walk_python(tree.root_node, abs_path, current_class=None, symbols=symbols)
    return symbols


def _walk_python(node, abs_path: str, current_class: str | None, symbols: list[Symbol]) -> None:
    if node.type == "class_definition":
        name_node = node.child_by_field_name("name")
        name = _node_text(name_node)
        if name:
            symbols.append(Symbol(
                kind="Class",
                name=name,
                file=abs_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
            ))
            # Walk children with this class as context
            for child in node.children:
                _walk_python(child, abs_path, current_class=name, symbols=symbols)
        return  # already recursed

    if node.type == "function_definition":
        name_node = node.child_by_field_name("name")
        name = _node_text(name_node)
        if name:
            kind = "Method" if current_class is not None else "Function"
            symbols.append(Symbol(
                kind=kind,
                name=name,
                file=abs_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                parent=current_class,
            ))
        # Still recurse into function body for nested classes/functions
        for child in node.children:
            _walk_python(child, abs_path, current_class=current_class, symbols=symbols)
        return

    for child in node.children:
        _walk_python(child, abs_path, current_class=current_class, symbols=symbols)


def parse_typescript(path: Path) -> list[Symbol]:
    """Parse a JS/TS file and return Class, Function, and Method symbols.

    Uses the tree-sitter-javascript grammar which covers structural JS/TS nodes.
    Arrow functions assigned to const are not captured here — TODO(M4).
    """
    if not _is_parseable(path):
        return []

    source = path.read_bytes()
    parser = Parser(_JS_LANGUAGE)
    tree = parser.parse(source)
    abs_path = str(path.resolve())

    symbols: list[Symbol] = []
    _walk_js(tree.root_node, abs_path, current_class=None, symbols=symbols)
    return symbols


def _walk_js(node, abs_path: str, current_class: str | None, symbols: list[Symbol]) -> None:
    if node.type == "class_declaration":
        name_node = node.child_by_field_name("name")
        name = _node_text(name_node)
        if name:
            symbols.append(Symbol(
                kind="Class",
                name=name,
                file=abs_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
            ))
            for child in node.children:
                _walk_js(child, abs_path, current_class=name, symbols=symbols)
        return

    if node.type == "method_definition":
        name_node = node.child_by_field_name("name")
        name = _node_text(name_node)
        if name and current_class is not None:
            symbols.append(Symbol(
                kind="Method",
                name=name,
                file=abs_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                parent=current_class,
            ))
        for child in node.children:
            _walk_js(child, abs_path, current_class=current_class, symbols=symbols)
        return

    if node.type == "function_declaration":
        name_node = node.child_by_field_name("name")
        name = _node_text(name_node)
        if name and current_class is None:
            symbols.append(Symbol(
                kind="Function",
                name=name,
                file=abs_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
            ))
        for child in node.children:
            _walk_js(child, abs_path, current_class=current_class, symbols=symbols)
        return

    for child in node.children:
        _walk_js(child, abs_path, current_class=current_class, symbols=symbols)
