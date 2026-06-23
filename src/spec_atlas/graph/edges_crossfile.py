"""Extract cross-file edges (imports, inferred calls) via tree-sitter."""

from __future__ import annotations

import re
import uuid

from spec_atlas.db.analysis import Edge, File, Node


class CrossFileEdgeExtractor:
    """Extract edges across files (imports, inferred calls)."""

    @staticmethod
    def extract(
        repo_id: uuid.UUID,
        files: list[File],
        nodes_by_file: dict[uuid.UUID, list[Node]],
        file_contents: dict[uuid.UUID, str],
    ) -> list[Edge]:
        """Extract cross-file edges.

        Args:
            repo_id: Repository ID.
            files: List of File objects in the repo.
            nodes_by_file: Dict mapping file_id → list[Node].
            file_contents: Dict mapping file_id → source code.

        Returns:
            List of Edge objects (cross-file imports + inferred calls).
        """
        edges = []

        # Build a map of (language, qualified_name) → node for resolution
        nodes_by_qname = {}
        file_id_by_qname = {}
        for file_id, nodes in nodes_by_file.items():
            for node in nodes:
                qname_key = (node.language, node.qualified_name)
                if qname_key not in nodes_by_qname:
                    nodes_by_qname[qname_key] = []
                nodes_by_qname[qname_key].append(node)
                file_id_by_qname[qname_key] = file_id

        # Extract imports for each file
        for file in files:
            if file.id not in file_contents:
                continue

            content = file_contents[file.id]
            file_nodes = nodes_by_file.get(file.id, [])

            if file.language == "python":
                edges.extend(
                    _extract_python_imports(file, content, file_nodes, nodes_by_qname, repo_id)
                )
            elif file.language in ("typescript", "javascript"):
                edges.extend(
                    _extract_ts_imports(file, content, file_nodes, nodes_by_qname, repo_id)
                )

        return edges


def _extract_python_imports(
    file: File,
    content: str,
    file_nodes: list[Node],
    nodes_by_qname: dict[tuple[str, str], list[Node]],
    repo_id: uuid.UUID,
) -> list[Edge]:
    """Extract Python import edges."""
    edges = []

    # Parse import statements using regex
    # import X, import X as Y, from X import Y, from X import Y as Z
    import_patterns = [
        (r"^import\s+(\w+(?:\.\w+)*)\s*(?:as\s+(\w+))?", "import"),
        (r"^from\s+(\w+(?:\.\w+)*)\s+import\s+(\w+(?:\s*,\s*\w+)*)", "from_import"),
    ]

    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        for pattern, import_type in import_patterns:
            match = re.match(pattern, line)
            if not match:
                continue

            if import_type == "import":
                # import X [as Y]
                module_name = match.group(1)

                # Try to find a matching node
                qname_key = ("python", module_name)
                if qname_key in nodes_by_qname:
                    for dst_node in nodes_by_qname[qname_key]:
                        if dst_node.repo_id == repo_id and dst_node.file_id != file.id:
                            # Find a source node (module-level or first in file)
                            src_node = None
                            for node in file_nodes:
                                if node.kind == "function" or node.kind == "class":
                                    src_node = node
                                    break
                            if src_node:
                                edges.append(
                                    Edge(
                                        repo_id=repo_id,
                                        src_node_id=src_node.id,
                                        dst_node_id=dst_node.id,
                                        kind="imports",
                                        confidence=1.0,
                                    )
                                )
                                break

            elif import_type == "from_import":
                # from X import Y [, Z, ...]
                module_name = match.group(1)
                imports = match.group(2).split(",")

                for imp in imports:
                    imp = imp.strip()
                    symbol_name = imp.split()[0]  # Handle "import X as Y"

                    # Try to resolve to a node
                    qname_key = ("python", f"{module_name}.{symbol_name}")
                    found = False

                    if qname_key in nodes_by_qname:
                        for dst_node in nodes_by_qname[qname_key]:
                            if dst_node.repo_id == repo_id and dst_node.file_id != file.id:
                                src_node = None
                                for node in file_nodes:
                                    if node.kind == "function" or node.kind == "class":
                                        src_node = node
                                        break
                                if src_node:
                                    edges.append(
                                        Edge(
                                            repo_id=repo_id,
                                            src_node_id=src_node.id,
                                            dst_node_id=dst_node.id,
                                            kind="imports",
                                            confidence=1.0,
                                        )
                                    )
                                    found = True
                                    break

                    if not found:
                        # Try just the module name
                        qname_key = ("python", module_name)
                        if qname_key in nodes_by_qname:
                            for dst_node in nodes_by_qname[qname_key]:
                                if dst_node.repo_id == repo_id and dst_node.file_id != file.id:
                                    src_node = None
                                    for node in file_nodes:
                                        if node.kind == "function" or node.kind == "class":
                                            src_node = node
                                            break
                                    if src_node:
                                        edges.append(
                                            Edge(
                                                repo_id=repo_id,
                                                src_node_id=src_node.id,
                                                dst_node_id=dst_node.id,
                                                kind="imports",
                                                confidence=1.0,
                                            )
                                        )
                                        break

    return edges


def _extract_ts_imports(
    file: File,
    content: str,
    file_nodes: list[Node],
    nodes_by_qname: dict[tuple[str, str], list[Node]],
    repo_id: uuid.UUID,
) -> list[Edge]:
    """Extract TypeScript/JavaScript import edges via tree-sitter CST."""
    edges = []

    module_paths = _parse_ts_import_paths(content, file.language or "typescript")

    for module_path in module_paths:
        lang_key = "typescript" if file.language in ("typescript", "tsx") else "javascript"
        qname_key = (lang_key, module_path)

        if qname_key in nodes_by_qname:
            for dst_node in nodes_by_qname[qname_key]:
                if dst_node.repo_id == repo_id and dst_node.file_id != file.id:
                    src_node = None
                    for node in file_nodes:
                        if node.kind in ("function", "class"):
                            src_node = node
                            break
                    if src_node:
                        edges.append(
                            Edge(
                                repo_id=repo_id,
                                src_node_id=src_node.id,
                                dst_node_id=dst_node.id,
                                kind="imports",
                                confidence=1.0,
                            )
                        )
                        break

    return edges


def _parse_ts_import_paths(content: str, language: str) -> list[str]:
    """Extract module paths from import/export declarations via tree-sitter.

    Returns a list of raw specifier strings (e.g. './utils', 'react').
    """
    try:
        from spec_atlas.parse.treesitter import parse_ts

        tree = parse_ts(content, language)
    except Exception:
        return _parse_ts_import_paths_regex_fallback(content)

    paths: list[str] = []

    def _walk(node) -> None:
        if node.type in ("import_statement", "export_statement"):
            for child in node.children:
                if child.type == "string":
                    raw = child.text
                    s = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else (raw or "")
                    # Strip surrounding quotes
                    s = s.strip("'\"` ")
                    if s:
                        paths.append(s)
            return
        for child in node.children:
            _walk(child)

    _walk(tree.root_node)
    return paths


def _parse_ts_import_paths_regex_fallback(content: str) -> list[str]:
    """Regex fallback for import path extraction."""
    import re

    pattern = r'import\s+(?:[\w{}\s,*]+)\s+from\s+["\']([^"\']+)["\']'
    return re.findall(pattern, content)
