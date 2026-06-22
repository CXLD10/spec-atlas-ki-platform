"""Thin tree-sitter wrapper for Python CST parsing.

F-000 only needs to prove the local parsing toolchain works. This module keeps the
surface small so F-002 can build symbol extraction on top of a stable entrypoint.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import tree_sitter_python
from tree_sitter import Language, Node, Parser, Tree


@lru_cache
def get_python_language() -> Language:
    """Return the cached Python grammar loaded from the local wheel."""
    return Language(tree_sitter_python.language())


@lru_cache
def get_python_parser() -> Parser:
    """Return a parser configured with the Python grammar."""
    return Parser(get_python_language())


def parse_python(source: str | bytes) -> Tree:
    """Parse Python source text or bytes into a CST."""
    data = source.encode("utf-8") if isinstance(source, str) else source
    return get_python_parser().parse(data)


def parse_python_file(path: str | Path) -> Tree:
    """Read and parse a Python source file from disk."""
    return parse_python(Path(path).read_bytes())


def top_level_named_nodes(tree: Tree) -> list[Node]:
    """Return named top-level nodes from a parsed module."""
    return [child for child in tree.root_node.children if child.is_named]
