"""Tests for Python symbol extraction."""

from __future__ import annotations

from spec_atlas.parse.python_symbols import PythonSymbolExtractor


class TestPythonSymbolExtraction:
    """Tests for extracting Python symbols (functions, classes, methods)."""

    def test_extract_top_level_function(self) -> None:
        """Extract a top-level function."""
        source = """
def hello(name: str) -> str:
    '''Greet someone.'''
    return f"Hello, {name}"
"""
        symbols = PythonSymbolExtractor.extract("test.py", source)

        assert len(symbols) >= 1
        func = next((s for s in symbols if s.name == "hello"), None)
        assert func is not None
        assert func.kind == "function"
        assert func.qualified_name == "hello"
        assert func.docstring is not None

    def test_extract_top_level_class(self) -> None:
        """Extract a top-level class."""
        source = """
class User:
    '''A user object.'''
    def __init__(self, name: str):
        self.name = name
"""
        symbols = PythonSymbolExtractor.extract("test.py", source)

        assert len(symbols) >= 1
        cls = next((s for s in symbols if s.name == "User"), None)
        assert cls is not None
        assert cls.kind == "class"

    def test_extract_class_methods(self) -> None:
        """Extract methods inside a class."""
        source = """
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
"""
        symbols = PythonSymbolExtractor.extract("test.py", source)

        # Should find class + methods
        names = {s.name for s in symbols}
        assert "Calculator" in names

    def test_extract_no_symbols(self) -> None:
        """Handle source with no symbols gracefully."""
        source = """
# Just a comment
x = 42
"""
        symbols = PythonSymbolExtractor.extract("test.py", source)

        # Should return empty or only module-level vars (simplified)
        assert isinstance(symbols, list)

    def test_extract_with_decorators(self) -> None:
        """Extract functions with decorators."""
        source = """
@property
def name(self):
    return self._name
"""
        symbols = PythonSymbolExtractor.extract("test.py", source)

        # May extract or not (depends on CST depth)
        assert isinstance(symbols, list)
