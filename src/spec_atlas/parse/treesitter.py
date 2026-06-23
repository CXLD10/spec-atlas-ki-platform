"""Thin tree-sitter wrapper for Python, TypeScript, and JavaScript CST parsing."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_typescript
from tree_sitter import Language, Node, Parser, Tree


@lru_cache
def get_python_language() -> Language:
    """Return the cached Python grammar loaded from the local wheel."""
    return Language(tree_sitter_python.language())


@lru_cache
def get_python_parser() -> Parser:
    """Return a parser configured with the Python grammar."""
    return Parser(get_python_language())


@lru_cache
def get_typescript_language() -> Language:
    return Language(tree_sitter_typescript.language_typescript())


@lru_cache
def get_tsx_language() -> Language:
    return Language(tree_sitter_typescript.language_tsx())


@lru_cache
def get_javascript_language() -> Language:
    return Language(tree_sitter_javascript.language())


def get_ts_parser(lang: str) -> Parser:
    """Return a parser for 'typescript', 'tsx', or 'javascript'."""
    if lang == "typescript":
        return Parser(get_typescript_language())
    if lang in ("tsx", "jsx"):
        return Parser(get_tsx_language())
    return Parser(get_javascript_language())


def parse_python(source: str | bytes) -> Tree:
    """Parse Python source text or bytes into a CST."""
    data = source.encode("utf-8") if isinstance(source, str) else source
    return get_python_parser().parse(data)


def parse_ts(source: str | bytes, lang: str = "typescript") -> Tree:
    """Parse TypeScript/JavaScript source into a CST."""
    data = source.encode("utf-8") if isinstance(source, str) else source
    return get_ts_parser(lang).parse(data)


def parse_python_file(path: str | Path) -> Tree:
    """Read and parse a Python source file from disk."""
    return parse_python(Path(path).read_bytes())


def top_level_named_nodes(tree: Tree) -> list[Node]:
    """Return named top-level nodes from a parsed module."""
    return [child for child in tree.root_node.children if child.is_named]
