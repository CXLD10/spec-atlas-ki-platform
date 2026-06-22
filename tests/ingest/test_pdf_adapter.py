"""Tests for PDF adapter."""

from __future__ import annotations

import tempfile
from pathlib import Path

import fitz
import pytest

from spec_atlas.ingest.adapters.pdf import PDFAdapter
from spec_atlas.ingest.source_unit import SourceType


def create_test_pdf(file_path: str, num_pages: int = 2) -> None:
    """Create a minimal PDF with the given number of pages.

    Args:
        file_path: Path where the PDF should be created.
        num_pages: Number of pages to create.
    """
    doc = fitz.open()

    for i in range(num_pages):
        page = doc.new_page()
        text = f"This is page {i + 1} of the test PDF.\n" * 5
        page.insert_text((50, 50), text)

    doc.save(file_path)
    doc.close()


@pytest.mark.anyio
async def test_pdf_adapter_parses_pages():
    """Test that PDF adapter extracts pages correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = str(Path(tmpdir) / "test.pdf")
        create_test_pdf(pdf_path, num_pages=3)

        adapter = PDFAdapter("test.pdf", pdf_path)
        units = await adapter.ingest()

        assert len(units) == 3, "Should extract 3 pages"
        assert all(unit.source_type() == "pdf" for unit in units)


@pytest.mark.anyio
async def test_pdf_adapter_page_locators():
    """Test that page locators are formatted correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = str(Path(tmpdir) / "document.pdf")
        create_test_pdf(pdf_path, num_pages=2)

        adapter = PDFAdapter("document.pdf", pdf_path)
        units = await adapter.ingest()

        assert units[0].provenance.locator == "document.pdf:p.1"
        assert units[1].provenance.locator == "document.pdf:p.2"


@pytest.mark.anyio
async def test_pdf_adapter_source_type():
    """Test that provenance source_type is PDF."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = str(Path(tmpdir) / "sample.pdf")
        create_test_pdf(pdf_path)

        adapter = PDFAdapter("sample.pdf", pdf_path)
        units = await adapter.ingest()

        assert units[0].provenance.source_type == SourceType.PDF


@pytest.mark.anyio
async def test_pdf_adapter_extracts_text():
    """Test that page text is extracted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = str(Path(tmpdir) / "content.pdf")
        create_test_pdf(pdf_path)

        adapter = PDFAdapter("content.pdf", pdf_path)
        units = await adapter.ingest()

        assert len(units) > 0
        assert "page 1" in units[0].text.lower()


def test_pdf_adapter_invalid_file():
    """Test that PDFAdapter raises ValueError for invalid PDF."""
    adapter = PDFAdapter("nonexistent.pdf", "/nonexistent/path.pdf")

    with pytest.raises(ValueError, match="Failed to parse PDF"):
        import asyncio

        asyncio.run(adapter.ingest())
