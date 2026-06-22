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
