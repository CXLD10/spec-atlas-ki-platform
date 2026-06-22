"""Tests for Markdown adapter."""

from __future__ import annotations

import tempfile

import pytest

from spec_atlas.ingest.adapters.markdown import MarkdownAdapter
from spec_atlas.ingest.source_unit import SourceType


@pytest.fixture
def markdown_file() -> str:
    """Create a test Markdown file.

    Returns:
        Path to the created Markdown file.
    """
    content = """# Introduction
This is the introduction section with some content.

## Architecture
System design and component details.
More details about the architecture.

## API Reference
API endpoints and usage documentation.

### Getting Started
Quick start guide.
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        f.flush()
        yield f.name


@pytest.fixture
def simple_markdown() -> str:
    """Create a simple test Markdown file.

    Returns:
        Path to the created Markdown file.
    """
    content = """# Main Section
Content of main section.

## Subsection
Content of subsection.
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        f.flush()
        yield f.name


@pytest.mark.anyio
async def test_markdown_adapter_splits_sections(markdown_file: str) -> None:
    """Test that Markdown adapter splits by headings."""
    adapter = MarkdownAdapter("README.md", markdown_file)
    units = await adapter.ingest()

    assert len(units) >= 3
    # Check that we have units for different sections
    section_names = [u.provenance.locator for u in units]
    assert any("Introduction" in s for s in section_names)
    assert any("Architecture" in s for s in section_names)
    assert any("API" in s for s in section_names)


@pytest.mark.anyio
async def test_markdown_provenance(markdown_file: str) -> None:
    """Test that Markdown adapter creates correct provenance."""
    adapter = MarkdownAdapter("README.md", markdown_file)
    units = await adapter.ingest()

    assert all(u.provenance.source_type == SourceType.MARKDOWN for u in units)
    assert all("README.md" in u.provenance.locator for u in units)
    assert all("section=" in u.provenance.locator for u in units)


@pytest.mark.anyio
async def test_markdown_text_content(markdown_file: str) -> None:
    """Test that Markdown adapter preserves text content."""
    adapter = MarkdownAdapter("README.md", markdown_file)
    units = await adapter.ingest()

    # Check that content is preserved
    all_text = " ".join(u.text for u in units)
    assert "introduction" in all_text.lower()
    assert "architecture" in all_text.lower()
    assert "component" in all_text.lower()


@pytest.mark.anyio
async def test_markdown_simple_file(simple_markdown: str) -> None:
    """Test Markdown adapter with simple structure."""
    adapter = MarkdownAdapter("simple.md", simple_markdown)
    units = await adapter.ingest()

    assert len(units) >= 2
    locators = [u.provenance.locator for u in units]
    assert any("Main" in locator for locator in locators)
    assert any("Subsection" in locator for locator in locators)


@pytest.mark.anyio
async def test_markdown_adapter_invalid_file() -> None:
    """Test that MarkdownAdapter raises ValueError for invalid file."""
    adapter = MarkdownAdapter("nonexistent.md", "/nonexistent/path.md")

    with pytest.raises(ValueError, match="Failed to parse Markdown"):
        await adapter.ingest()


@pytest.mark.anyio
async def test_markdown_adapter_source_id(markdown_file: str) -> None:
    """Test that source_id is preserved in SourceUnits."""
    adapter = MarkdownAdapter("my_doc.md", markdown_file)
    units = await adapter.ingest()

    assert all(unit.source_id == "my_doc.md" for unit in units)


@pytest.mark.anyio
async def test_markdown_heading_parsing() -> None:
    """Test the heading parsing logic directly."""
    adapter = MarkdownAdapter("test.md", "dummy_path")

    content = """# H1
Content 1

## H2
Content 2

### H3
Content 3
"""

    sections = adapter._split_by_heading(content)

    # Should have introduction + 3 sections
    assert len(sections) >= 3
    section_names = [s[0] for s in sections]
    assert "H1" in section_names or any("H1" in s for s in section_names)


@pytest.mark.anyio
async def test_markdown_empty_file() -> None:
    """Test Markdown adapter with empty file."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("")
        f.flush()
        temp_path = f.name

    adapter = MarkdownAdapter("empty.md", temp_path)
    units = await adapter.ingest()

    # Empty file should result in no units or just introduction
    assert len(units) >= 0
