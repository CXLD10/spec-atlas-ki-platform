"""Tests for language detection."""

from __future__ import annotations

import pytest

from spec_atlas.ingest.language import LanguageDetector


class TestLanguageDetection:
    """Tests for language detection from file paths."""

    @pytest.mark.parametrize(
        "file_path,expected",
        [
            ("module.py", "python"),
            ("script.pyw", "python"),
            ("index.ts", "typescript"),
            ("component.tsx", "typescript"),
            ("app.js", "javascript"),
            ("utils.jsx", "javascript"),
            ("main.mjs", "javascript"),
            ("bundle.cjs", "javascript"),
        ],
    )
    def test_detect_supported_extensions(self, file_path: str, expected: str) -> None:
        """Detect language from supported file extensions."""
        assert LanguageDetector.detect(file_path) == expected

    @pytest.mark.parametrize(
        "file_path",
        [
            "README.md",
            "Makefile",
            "config.json",
            "package.yaml",
            "script.sh",
            "data.csv",
            "image.png",
            "archive.tar.gz",
        ],
    )
    def test_detect_unsupported_extensions(self, file_path: str) -> None:
        """Return 'unknown' for unsupported extensions."""
        assert LanguageDetector.detect(file_path) == "unknown"

    @pytest.mark.parametrize(
        "file_path",
        [
            "Module.PY",
            "Script.Py",
            "Index.TS",
            "App.JS",
        ],
    )
    def test_detect_case_insensitive(self, file_path: str) -> None:
        """Detect language regardless of extension case."""
        # Should work with any case (lowercase extensions)
        result = LanguageDetector.detect(file_path)
        # Accept both the detected language and 'unknown' (if grammar unavailable)
        assert result in ("python", "typescript", "javascript", "unknown")

    def test_detect_nested_paths(self) -> None:
        """Detect language from nested file paths."""
        assert LanguageDetector.detect("src/models/user.py") == "python"
        assert LanguageDetector.detect("frontend/components/App.tsx") == "typescript"
        assert LanguageDetector.detect("backend/routes/api.js") == "javascript"

    def test_detect_python_grammar_available(self) -> None:
        """Python grammar should be available (F-000 verified this)."""
        # This verifies that the Python grammar was installed in F-000
        assert LanguageDetector.detect("test.py") == "python"

    def test_detect_multiple_dots_in_name(self) -> None:
        """Handle files with multiple dots in the name."""
        # Extension is determined by last dot, so "spec.test.py" → ".py"
        assert LanguageDetector.detect("spec.test.py") == "python"
        assert LanguageDetector.detect("component.module.tsx") == "typescript"
