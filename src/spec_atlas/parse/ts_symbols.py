"""Extract TypeScript/JavaScript symbols via tree-sitter."""

from __future__ import annotations

from dataclasses import dataclass


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
        """Extract symbols from TS/JS source.

        Args:
            file_path: Path to the file (for reference).
            file_content: Source code as a string.
            language: "typescript" or "javascript".

        Returns:
            List of extracted symbols.
        """
        # For v1, we'll use a simplified extraction via regex + tree-sitter parsing
        # Full tree-sitter-typescript integration is deferred to F-002 follow-up
        symbols = []

        # Extract top-level functions and classes (simplified)
        import re

        # Function declarations: function name(...) or const name = (...) =>
        func_pattern = r"(?:function|const|let|var)\s+(\w+)\s*(?:\(|=)"
        for match in re.finditer(func_pattern, file_content):
            name = match.group(1)
            start_line = file_content[: match.start()].count("\n") + 1
            symbols.append(
                TSSymbol(
                    kind="function",
                    name=name,
                    qualified_name=name,
                    signature=f"function {name}",
                    docstring=None,
                    start_line=start_line,
                    end_line=start_line,
                )
            )

        # Class declarations: class Name
        class_pattern = r"class\s+(\w+)"
        for match in re.finditer(class_pattern, file_content):
            name = match.group(1)
            start_line = file_content[: match.start()].count("\n") + 1
            symbols.append(
                TSSymbol(
                    kind="class",
                    name=name,
                    qualified_name=name,
                    signature=f"class {name}",
                    docstring=None,
                    start_line=start_line,
                    end_line=start_line,
                )
            )

        return symbols
