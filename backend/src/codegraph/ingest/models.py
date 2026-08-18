from dataclasses import dataclass
from typing import Literal

SymbolKind = Literal["File", "Class", "Function", "Method"]


@dataclass
class Symbol:
    kind: SymbolKind
    name: str
    file: str  # absolute path
    start_line: int  # 1-indexed
    end_line: int
    parent: str | None = None  # simple name of containing class
