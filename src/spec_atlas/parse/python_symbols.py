"""Extract Python symbols (functions, classes, methods) via tree-sitter."""

from __future__ import annotations

from dataclasses import dataclass

from spec_atlas.parse.treesitter import parse_python


@dataclass
class PythonSymbol:
    """A Python symbol extracted from the CST."""

    kind: str  # "function" | "class" | "method"
    name: str
    qualified_name: str
    signature: str
    docstring: str | None
    start_line: int
    end_line: int


class PythonSymbolExtractor:
    """Extract symbols from Python source via tree-sitter."""

    @staticmethod
    def extract(file_path: str, file_content: str) -> list[PythonSymbol]:
        """Extract Python symbols from source.

        Args:
            file_path: Path to the Python file (for reference).
            file_content: Source code as a string.

        Returns:
            List of extracted symbols.
        """
        tree = parse_python(file_content)
        symbols = []

        # Walk the CST and extract top-level functions/classes
        _extract_symbols_recursive(tree.root_node, file_content, "", symbols)

        return symbols


def _extract_symbols_recursive(
    node, file_content: str, scope_prefix: str, symbols: list[PythonSymbol]
) -> None:
    """Recursively extract symbols from tree-sitter CST."""
    if node.type == "function_definition":
        sym = _extract_function(node, file_content, scope_prefix)
        if sym:
            symbols.append(sym)
            # Don't recurse into nested functions yet (simplified for v1)

    elif node.type == "class_definition":
        sym = _extract_class(node, file_content, scope_prefix)
        if sym:
            symbols.append(sym)
            # Recurse to find methods inside the class
            class_name = sym.name
            new_scope = f"{scope_prefix}{class_name}" if scope_prefix else class_name
            for child in node.children:
                if child.type == "block":
                    for stmt in child.children:
                        if stmt.type == "function_definition":
                            method = _extract_function(
                                stmt, file_content, new_scope, is_method=True
                            )
                            if method:
                                symbols.append(method)

    else:
        # Recurse to children
        for child in node.children:
            _extract_symbols_recursive(child, file_content, scope_prefix, symbols)


def _extract_function(
    node, file_content: str, scope_prefix: str, is_method: bool = False
) -> PythonSymbol | None:
    """Extract a function or method symbol."""
    name_node = None
    params_node = None
    body_node = None

    for child in node.children:
        if child.type == "identifier":
            name_node = child
        elif child.type == "parameters":
            params_node = child
        elif child.type == "block":
            body_node = child

    if not name_node:
        return None

    name = name_node.text.decode() if isinstance(name_node.text, bytes) else name_node.text
    qualified_name = f"{scope_prefix}.{name}" if scope_prefix else name
    kind = "method" if is_method else "function"

    # Signature: function name and parameters
    start = node.start_byte
    end = params_node.end_byte if params_node else node.end_byte
    signature = file_content[start:end].strip()

    # Docstring: first statement in body if it's a string
    docstring = None
    if body_node:
        docstring = _extract_docstring(body_node, file_content)

    return PythonSymbol(
        kind=kind,
        name=name,
        qualified_name=qualified_name,
        signature=signature,
        docstring=docstring,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
    )


def _extract_class(node, file_content: str, scope_prefix: str) -> PythonSymbol | None:
    """Extract a class symbol."""
    name_node = None
    body_node = None

    for child in node.children:
        if child.type == "identifier":
            name_node = child
        elif child.type == "block":
            body_node = child

    if not name_node:
        return None

    name = name_node.text.decode() if isinstance(name_node.text, bytes) else name_node.text
    qualified_name = f"{scope_prefix}.{name}" if scope_prefix else name

    # Signature: class line
    signature = file_content[node.start_byte : node.start_byte + 200].split("\n")[0].strip()

    # Docstring
    docstring = None
    if body_node:
        docstring = _extract_docstring(body_node, file_content)

    return PythonSymbol(
        kind="class",
        name=name,
        qualified_name=qualified_name,
        signature=signature,
        docstring=docstring,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
    )


def _extract_docstring(block_node, file_content: str) -> str | None:
    """Extract docstring from a block (first string literal)."""
    for child in block_node.children:
        if child.type == "expression_statement":
            for subchild in child.children:
                if subchild.type == "string":
                    subchild_text = subchild.text
                    docstring_text = (
                        subchild_text.decode()
                        if isinstance(subchild_text, bytes)
                        else subchild_text
                    )
                    # Strip quotes
                    docstring_text = docstring_text.strip("'\"")
                    return docstring_text if docstring_text else None
    return None
