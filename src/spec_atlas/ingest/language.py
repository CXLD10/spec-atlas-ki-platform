"""Language detection per file."""

from __future__ import annotations

import logging
from pathlib import Path

from spec_atlas.parse.treesitter import get_python_language

logger = logging.getLogger(__name__)

# Extension → language mapping
_EXTENSION_MAP = {
    ".py": "python",
    ".pyw": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
}


class LanguageDetector:
    """Detect programming language from file path."""

    @staticmethod
    def detect(file_path: str) -> str:
        """Detect language for a file.

        Args:
            file_path: Path to the file.

        Returns:
            Language name: "python", "typescript", "javascript", or "unknown".
        """
        path = Path(file_path)
        extension = path.suffix.lower()

        # Check extension map
        if extension in _EXTENSION_MAP:
            language = _EXTENSION_MAP[extension]

            # Verify tree-sitter grammar is available
            if not _grammar_available(language):
                logger.debug(f"Grammar not available for {language}, marking unknown")
                return "unknown"

            return language

        return "unknown"


def _grammar_available(language: str) -> bool:
    """Check if tree-sitter grammar is available for the language.

    Args:
        language: Language name.

    Returns:
        True if the grammar loads successfully.
    """
    try:
        if language == "python":
            get_python_language()
            return True
    except Exception as e:
        logger.debug(f"Grammar check failed for {language}: {e}")
        return False

    # TypeScript/JavaScript grammars are not checked in v1 (just extension-based)
    if language in ("typescript", "javascript"):
        return True

    return False
