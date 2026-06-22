"""Adapter for PDF documents using PyMuPDF."""

from __future__ import annotations

import logging

import fitz

from spec_atlas.ingest.adapters.base import SourceAdapter
from spec_atlas.ingest.source_unit import Provenance, SourceType, SourceUnit

logger = logging.getLogger(__name__)


class PDFAdapter(SourceAdapter):
    """Adapter for PDF documents."""

    def __init__(self, source_id: str, file_path: str):
        """Initialize PDF adapter.

        Args:
            source_id: Unique identifier (filename or document name).
            file_path: Absolute path to the PDF file.
        """
        super().__init__(source_id)
        self.file_path = file_path

    async def ingest(self) -> list[SourceUnit]:
        """Parse PDF into page-level SourceUnits.

        Returns:
            List of SourceUnit, one per page with text content.

        Raises:
            ValueError: If PDF cannot be opened or parsed.
        """
        units = []

        try:
            doc = fitz.open(self.file_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                # Only create unit if page has content
                if text.strip():
                    unit = SourceUnit(
                        source_id=self.source_id,
                        text=text,
                        provenance=Provenance(
                            source_type=SourceType.PDF,
                            locator=f"{self.source_id}:p.{page_num + 1}",  # 1-indexed
                            source_id=self.source_id,
                        ),
                    )
                    units.append(unit)

            doc.close()

        except Exception as e:
            raise ValueError(f"Failed to parse PDF {self.file_path}: {e}") from e

        if not units:
            logger.warning(f"PDF {self.source_id} contains no extractable text")

        logger.info(f"PDF adapter ingested {len(units)} pages from {self.source_id}")
        return units
