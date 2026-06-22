"""Tests for SourceUnit abstraction."""

from __future__ import annotations

from spec_atlas.ingest.source_unit import Provenance, SourceType, SourceUnit


def test_source_unit_creation():
    """Test SourceUnit creation with provenance."""
    prov = Provenance(
        source_type=SourceType.CODE,
        locator="src/main.py:42",
        source_id="https://github.com/example/repo",
    )
    unit = SourceUnit(
        source_id="https://github.com/example/repo",
        text="def foo(): pass",
        provenance=prov,
    )

    assert unit.source_id == "https://github.com/example/repo"
    assert unit.text == "def foo(): pass"
    assert unit.citation_locator() == "src/main.py:42"
    assert unit.source_type() == "code"


def test_source_unit_without_provenance():
    """Test SourceUnit without provenance."""
    unit = SourceUnit(
        source_id="unknown-source",
        text="some text",
    )

    assert unit.citation_locator() == "unknown"
    assert unit.source_type() is None


def test_provenance_fields():
    """Test provenance with different source types."""
    sources = [
        (SourceType.PDF, "document.pdf:15"),
        (SourceType.EXCEL, "sheet1:A2"),
        (SourceType.MARKDOWN, "README.md:100"),
        (SourceType.JIRA, "PROJ-123"),
        (SourceType.GIT, "abc123def"),
    ]

    for source_type, locator in sources:
        prov = Provenance(
            source_type=source_type,
            locator=locator,
            source_id="test-source",
        )
        assert prov.source_type == source_type
        assert prov.locator == locator
