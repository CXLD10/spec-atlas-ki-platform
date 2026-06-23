"""Extract TypeScript/JavaScript symbols via tree-sitter CST."""

from __future__ import annotations

from dataclasses import dataclass

from spec_atlas.parse.treesitter import parse_ts


@dataclass
class TSSymbol:
    """A TypeScript/JavaScript symbol extracted from the CST."""

    kind: str  # "function" | "class" | "method"
    name: str
    qualified_name: str
    signature: str
    docstring: str | None
    start_line: int
    end_line: int


class TypeScriptSymbolExtractor:
    """Extract symbols from TypeScript/JavaScript source via tree-sitter."""

    @staticmethod
    def extract(file_path: str, file_content: str, language: str) -> list[TSSymbol]:
        """Extract symbols from TS/JS source using the tree-sitter CST.

        Args:
            file_path: Path to the file (for qualified_name prefix).
            file_content: Source code as a string.
            language: "typescript", "tsx", "javascript", or "jsx".

        Returns:
            List of extracted symbols.
        """
        try:
            tree = parse_ts(file_content, language)
        except Exception:
            return []

        symbols: list[TSSymbol] = []
        _walk(tree.root_node, file_content, scope_prefix="", symbols=symbols)
        return symbols


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_FUNC_TYPES = {
    "function_declaration",
    "generator_function_declaration",
    "method_definition",
}

_ARROW_TYPES = {
    "arrow_function",
    "function",
    "generator_function",
}


def _text(node) -> str:
    raw = node.text
    return raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else (raw or "")


def _walk(node, source: str, scope_prefix: str, symbols: list[TSSymbol]) -> None:
    """Walk the CST recursively, extracting functions, arrow vars, and classes."""
    t = node.type

    if t in _FUNC_TYPES:
        sym = _extract_function(node, source, scope_prefix, is_method=(t == "method_definition"))
        if sym:
            symbols.append(sym)
        return  # don't recurse deeper into function bodies

    if t == "class_declaration" or t == "class":
        sym = _extract_class(node, source, scope_prefix)
        if sym:
            symbols.append(sym)
            new_scope = f"{scope_prefix}.{sym.name}" if scope_prefix else sym.name
            # Recurse into the class body to find methods
            for child in node.children:
                if child.type == "class_body":
                    for stmt in child.children:
                        if stmt.type in _FUNC_TYPES:
                            method = _extract_function(stmt, source, new_scope, is_method=True)
                            if method:
                                symbols.append(method)
        return

    if t == "lexical_declaration" or t == "variable_declaration":
        # const/let/var name = () => ... or = function ...
        for child in node.children:
            if child.type == "variable_declarator":
                _extract_var_declarator(child, source, scope_prefix, symbols)
        return

    if t == "export_statement":
        # export function ... / export const ... / export class ...
        for child in node.children:
            _walk(child, source, scope_prefix, symbols)
        return

    for child in node.children:
        _walk(child, source, scope_prefix, symbols)


_NAME_NODE_TYPES = {"identifier", "property_identifier", "type_identifier"}


def _find_name(node) -> str | None:
    for child in node.children:
        if child.type in _NAME_NODE_TYPES:
            return _text(child)
    return None


def _extract_function(node, source: str, scope_prefix: str, is_method: bool) -> TSSymbol | None:
    name = _find_name(node)
    if not name:
        return None
    qualified = f"{scope_prefix}.{name}" if scope_prefix else name
    kind = "method" if is_method else "function"
    sig = _signature_line(node, source)
    return TSSymbol(
        kind=kind,
        name=name,
        qualified_name=qualified,
        signature=sig,
        docstring=None,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
    )


def _extract_class(node, source: str, scope_prefix: str) -> TSSymbol | None:
    name = _find_name(node)
    if not name:
        return None
    qualified = f"{scope_prefix}.{name}" if scope_prefix else name
    sig = _signature_line(node, source)
    return TSSymbol(
        kind="class",
        name=name,
        qualified_name=qualified,
        signature=sig,
        docstring=None,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
    )


def _extract_var_declarator(
    node, source: str, scope_prefix: str, symbols: list[TSSymbol]
) -> None:
    """Handle `const name = () => ...` and `const name = function(...) {...}`."""
    name = None
    rhs = None
    for child in node.children:
        if child.type == "identifier" and name is None:
            name = _text(child)
        elif child.type in _ARROW_TYPES:
            rhs = child

    if name and rhs:
        qualified = f"{scope_prefix}.{name}" if scope_prefix else name
        sig = f"const {name} = {_signature_line(rhs, source)}"
        symbols.append(
            TSSymbol(
                kind="function",
                name=name,
                qualified_name=qualified,
                signature=sig,
                docstring=None,
                start_line=rhs.start_point[0] + 1,
                end_line=rhs.end_point[0] + 1,
            )
        )


def _signature_line(node, source: str) -> str:
    """Return the first line of the node's source text (stripped)."""
    raw = source[node.start_byte : node.end_byte]
    return raw.split("\n")[0].strip()[:200]
