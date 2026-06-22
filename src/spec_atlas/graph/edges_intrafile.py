"""Extract intra-file edges (calls, inherits, defines) via tree-sitter."""

from __future__ import annotations

import uuid

from spec_atlas.db.analysis import Edge, Node
from spec_atlas.parse.treesitter import parse_python


class IntraFileEdgeExtractor:
    """Extract edges within a single file (calls, inherits, defines)."""

    @staticmethod
    def extract(
        file_id: uuid.UUID,
        file_path: str,
        language: str,
        nodes: list[Node],
        file_content: str,
    ) -> list[Edge]:
        """Extract intra-file edges.

        Args:
            file_id: UUID of the file being analyzed.
            file_path: Path to the file (for reference).
            language: "python", "typescript", or "javascript".
            nodes: List of Node objects for this file.
            file_content: Source code as a string.

        Returns:
            List of Edge objects (intra-file calls, inherits, defines).
        """
        edges = []

        # Map qualified_name to node for fast lookup
        nodes_by_qname = {node.qualified_name: node for node in nodes}

        if language == "python":
            edges.extend(_extract_python_edges(file_content, nodes_by_qname, file_id))
        elif language in ("typescript", "javascript"):
            edges.extend(_extract_ts_edges(file_content, language, nodes_by_qname, file_id))

        return edges


def _extract_python_edges(
    file_content: str,
    nodes_by_qname: dict[str, Node],
    file_id: uuid.UUID,
) -> list[Edge]:
    """Extract Python intra-file edges (calls, inherits, defines)."""
    edges = []
    tree = parse_python(file_content)

    # First pass: extract defines (class → method relationships)
    # and collect class nodes
    class_nodes = {}
    for node in tree.root_node.children:
        if node.type == "class_definition":
            class_name = None
            for child in node.children:
                if child.type == "identifier":
                    class_name = child.text
                    if isinstance(class_name, bytes):
                        class_name = class_name.decode()
                    break
            if class_name:
                class_nodes[class_name] = node

    # Add defines edges
    for class_name, class_node in class_nodes.items():
        class_qname = class_name  # Top-level class
        if class_qname not in nodes_by_qname:
            continue

        class_src_node = nodes_by_qname[class_qname]

        # Find methods inside the class
        for child in class_node.children:
            if child.type == "block":
                for stmt in child.children:
                    if stmt.type == "function_definition":
                        method_name = None
                        for subchild in stmt.children:
                            if subchild.type == "identifier":
                                method_name = subchild.text
                                if isinstance(method_name, bytes):
                                    method_name = method_name.decode()
                                break
                        if method_name:
                            method_qname = f"{class_qname}.{method_name}"
                            if method_qname in nodes_by_qname:
                                method_node = nodes_by_qname[method_qname]
                                edges.append(
                                    Edge(
                                        repo_id=class_src_node.repo_id,
                                        src_node_id=class_src_node.id,
                                        dst_node_id=method_node.id,
                                        kind="defines",
                                        confidence=1.0,
                                    )
                                )

    # Second pass: extract inherits (class inheritance)
    for node in tree.root_node.children:
        if node.type == "class_definition":
            class_name = None
            base_name = None

            for child in node.children:
                if child.type == "identifier":
                    class_name = child.text
                    if isinstance(class_name, bytes):
                        class_name = class_name.decode()
                elif child.type == "argument_list":
                    # class Foo(BaseClass): ...
                    for arg in child.children:
                        if arg.type == "identifier":
                            base_name = arg.text
                            if isinstance(base_name, bytes):
                                base_name = base_name.decode()
                            break

            if class_name and base_name:
                src_qname = class_name
                dst_qname = base_name

                if src_qname in nodes_by_qname and dst_qname in nodes_by_qname:
                    src = nodes_by_qname[src_qname]
                    dst = nodes_by_qname[dst_qname]
                    edges.append(
                        Edge(
                            repo_id=src.repo_id,
                            src_node_id=src.id,
                            dst_node_id=dst.id,
                            kind="inherits",
                            confidence=1.0,
                        )
                    )

    # Third pass: extract calls (function/method calls)
    _extract_python_calls(tree.root_node, file_content, nodes_by_qname, edges)

    return edges


def _extract_python_calls(
    node, file_content: str, nodes_by_qname: dict[str, Node], edges: list[Edge]
) -> None:
    """Recursively extract Python call edges."""
    if node.type == "call":
        # Get the function being called
        for child in node.children:
            if child.type == "identifier":
                callee_name = child.text
                if isinstance(callee_name, bytes):
                    callee_name = callee_name.decode()

                # Try to match to a node by qualified_name
                if callee_name in nodes_by_qname:
                    # For now, assume it's a module-level function
                    # We don't know the caller in this simplified version,
                    # so we skip creating the edge for now
                    pass
                break
            elif child.type == "attribute":
                # Handle method calls like obj.method() or Class.method()
                # Extract the method name (rightmost identifier)
                method_name = None
                for subchild in reversed(child.children):
                    if subchild.type == "identifier":
                        method_name = subchild.text
                        if isinstance(method_name, bytes):
                            method_name = method_name.decode()
                        break

                # We'd need to track the receiver to know the qualified name
                # For v1, skip dynamic call tracking
                break

    # Recurse
    for child in node.children:
        _extract_python_calls(child, file_content, nodes_by_qname, edges)


def _extract_ts_edges(
    file_content: str,
    language: str,
    nodes_by_qname: dict[str, Node],
    file_id: uuid.UUID,
) -> list[Edge]:
    """Extract TypeScript/JavaScript intra-file edges (calls, inherits, defines)."""
    edges = []

    # Use regex-based extraction (v1 simplified)
    import re

    # Extract defines: for each class, add edge to each method
    class_pattern = r"class\s+(\w+)\s*(?:extends\s+(\w+))?\s*\{"
    for class_match in re.finditer(class_pattern, file_content):
        class_name = class_match.group(1)
        base_name = class_match.group(2)

        # Find methods inside this class
        # Find the opening brace
        brace_pos = file_content.find("{", class_match.start())
        if brace_pos == -1:
            continue

        # Simple heuristic: find methods until the next "}" at same brace level
        brace_level = 0
        class_end = brace_pos
        for i in range(brace_pos, len(file_content)):
            if file_content[i] == "{":
                brace_level += 1
            elif file_content[i] == "}":
                brace_level -= 1
                if brace_level == 0:
                    class_end = i
                    break

        class_body = file_content[brace_pos:class_end]

        # Extract methods from the class body
        method_pattern = r"(\w+)\s*\("
        for method_match in re.finditer(method_pattern, class_body):
            method_name = method_match.group(1)

            # Skip constructor and common keywords
            if method_name in ("constructor", "if", "for", "while", "switch"):
                continue

            method_qname = f"{class_name}.{method_name}"
            src_qname = class_name

            if src_qname in nodes_by_qname and method_qname in nodes_by_qname:
                src = nodes_by_qname[src_qname]
                dst = nodes_by_qname[method_qname]
                edges.append(
                    Edge(
                        repo_id=src.repo_id,
                        src_node_id=src.id,
                        dst_node_id=dst.id,
                        kind="defines",
                        confidence=1.0,
                    )
                )

        # Add inherits edge if base_name exists
        if base_name:
            src_qname = class_name
            dst_qname = base_name

            if src_qname in nodes_by_qname and dst_qname in nodes_by_qname:
                src = nodes_by_qname[src_qname]
                dst = nodes_by_qname[dst_qname]
                edges.append(
                    Edge(
                        repo_id=src.repo_id,
                        src_node_id=src.id,
                        dst_node_id=dst.id,
                        kind="inherits",
                        confidence=1.0,
                    )
                )

    return edges
