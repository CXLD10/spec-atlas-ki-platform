"""Normalized unit of knowledge from any source (code, PDF, Excel, Markdown, Jira, git)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class SourceType(StrEnum):
    """Source format type."""

    CODE = "code"
    PDF = "pdf"
    EXCEL = "excel"
    MARKDOWN = "markdown"
    JIRA = "jira"
    GIT = "git"


@dataclass
class Provenance:
    """Where a SourceUnit came from."""

    source_type: SourceType
    """Source format (code, PDF, etc.)."""
    locator: str
    """Citation locator: 'file:line', 'document:page', 'ticket:KEY', 'commit:sha', etc."""
    source_id: str
    """Unique identifier: repo URL, file path, ticket ID, etc."""


@dataclass
class SourceUnit:
    """Normalized unit of knowledge from any source."""

    source_id: str
    """Unique identifier for the source (repo URL, PDF filename, etc.)."""
    text: str
    """Raw content (code snippet, PDF text, markdown, etc.)."""
    structure: dict[str, Any] | None = None
    """Optional: parsed AST, tables, metadata, etc."""
    provenance: Provenance | None = None
    """Where this unit came from."""

    def citation_locator(self) -> str:
        """Return the citation string for answers."""
        if self.provenance:
            return self.provenance.locator
        return "unknown"

    def source_type(self) -> str | None:
        """Return the source type if available."""
        if self.provenance:
            return self.provenance.source_type.value
        return None
