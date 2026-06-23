"""Tests for TypeScript/JavaScript symbol extraction."""

from __future__ import annotations

from spec_atlas.parse.ts_symbols import TypeScriptSymbolExtractor


class TestTypeScriptSymbolExtraction:
    """Tests for extracting TS/JS symbols (functions, classes)."""

    def test_extract_function_declaration(self) -> None:
        """Extract a function declaration."""
        source = """
function greet(name: string): string {
  return `Hello, ${name}`;
}
"""
        symbols = TypeScriptSymbolExtractor.extract("test.ts", source, "typescript")

        assert len(symbols) >= 1
        func = next((s for s in symbols if s.name == "greet"), None)
        assert func is not None
        assert func.kind == "function"

    def test_extract_arrow_function(self) -> None:
        """Extract arrow function assignment."""
        source = """
const add = (a: number, b: number): number => {
  return a + b;
};
"""
        symbols = TypeScriptSymbolExtractor.extract("test.ts", source, "typescript")

        assert len(symbols) >= 1
        func = next((s for s in symbols if s.name == "add"), None)
        assert func is not None

    def test_extract_class_declaration(self) -> None:
        """Extract a class declaration."""
        source = """
class User {
  constructor(name: string) {
    this.name = name;
  }
}
"""
        symbols = TypeScriptSymbolExtractor.extract("test.ts", source, "typescript")

        assert len(symbols) >= 1
        cls = next((s for s in symbols if s.name == "User"), None)
        assert cls is not None
        assert cls.kind == "class"

    def test_extract_javascript(self) -> None:
        """Extract symbols from JavaScript source."""
        source = """
function hello() {
  console.log('hello');
}

class App {
  run() {}
}
"""
        symbols = TypeScriptSymbolExtractor.extract("test.js", source, "javascript")

        assert len(symbols) >= 1
        names = {s.name for s in symbols}
        assert "hello" in names or "App" in names

    def test_extract_no_symbols(self) -> None:
        """Handle source with no symbols gracefully."""
        source = """
// Just a comment
const x = 42;
"""
        symbols = TypeScriptSymbolExtractor.extract("test.ts", source, "typescript")

        # Should return list (may or may not include x)
        assert isinstance(symbols, list)


class TestTypeScriptSymbolsViaTreeSitter:
    """Verify that TypeScriptSymbolExtractor uses the real tree-sitter CST (F-014 Phase 5)."""

    def test_ts_symbols_via_treesitter(self) -> None:
        """TypeScriptSymbolExtractor uses tree-sitter CST, not regex.

        Proof: regex cannot distinguish `function` inside a string literal from
        a real function declaration. The CST parser correctly skips string content.
        """
        from spec_atlas.parse.ts_symbols import TypeScriptSymbolExtractor

        # This would confuse a naïve regex: 'function' inside a template literal
        source = """
const docstring = `
function notAFunction(x) { }
`;

function realFunction(a: string): void {
  console.log(a);
}
"""
        symbols = TypeScriptSymbolExtractor.extract("tricky.ts", source, "typescript")
        names = {s.name for s in symbols}

        # The real function should be found
        assert "realFunction" in names
        # 'notAFunction' is inside a template literal — CST skips it; regex would find it
        assert "notAFunction" not in names, (
            "CST-based extractor should not find symbols inside string literals"
        )

    def test_ts_line_numbers_accurate(self) -> None:
        """start_line and end_line are accurate (requires CST, not regex)."""
        from spec_atlas.parse.ts_symbols import TypeScriptSymbolExtractor

        source = "// line 1\n// line 2\nfunction foo() {\n  return 1;\n}\n"
        symbols = TypeScriptSymbolExtractor.extract("lines.ts", source, "typescript")

        foo = next((s for s in symbols if s.name == "foo"), None)
        assert foo is not None
        assert foo.start_line == 3, f"Expected start_line=3, got {foo.start_line}"

    def test_method_inside_class_has_class_scope(self) -> None:
        """Methods inside a class have qualified_name = ClassName.methodName."""
        from spec_atlas.parse.ts_symbols import TypeScriptSymbolExtractor

        source = """
class Calculator {
  add(a: number, b: number): number {
    return a + b;
  }
}
"""
        symbols = TypeScriptSymbolExtractor.extract("calc.ts", source, "typescript")
        method = next((s for s in symbols if s.name == "add"), None)
        assert method is not None
        assert "Calculator" in method.qualified_name, (
            f"Expected qualified_name to contain 'Calculator', got {method.qualified_name!r}"
        )
        assert method.kind == "method"

    def test_import_path_extraction_uses_cst(self) -> None:
        """_parse_ts_import_paths uses tree-sitter CST to extract import specifiers."""
        from spec_atlas.graph.edges_crossfile import _parse_ts_import_paths

        source = """
import React from 'react';
import { useState, useEffect } from 'react';
import type { FC } from 'react';
import * as Utils from './utils';
// import { notAnImport } from 'commented-out';
"""
        paths = _parse_ts_import_paths(source, "typescript")
        assert "react" in paths
        assert "./utils" in paths
        # Commented-out import should NOT be present (CST ignores comments)
        assert "commented-out" not in paths, (
            "CST-based import extractor must not parse imports inside comments"
        )
