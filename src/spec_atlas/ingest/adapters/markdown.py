"""Adapter for Markdown files (.md)."""

from __future__ import annotations

import logging
import re

from spec_atlas.ingest.adapters.base import SourceAdapter
from spec_atlas.ingest.source_unit import Provenance, SourceType, SourceUnit

logger = logging.getLogger(__name__)


class MarkdownAdapter(SourceAdapter):
    """Adapter for Markdown files."""

    def __init__(self, source_id: str, file_path: str):
        """Initialize Markdown adapter.

        Args:
            source_id: Unique identifier (filename or document name).
            file_path: Absolute path to the Markdown file.
        """
        super().__init__(source_id)
        self.file_path = file_path

    async def ingest(self) -> list[SourceUnit]:
        """Parse Markdown file into section-level SourceUnits.

        Returns:
            List of SourceUnit, one per section with provenance linking to heading.

        Raises:
            ValueError: If Markdown file cannot be opened or parsed.
        """
        units = []

        try:
            with open(self.file_path, encoding="utf-8") as f:
                content = f.read()

            # Split by headings (# , ## , ### , etc.)
            sections = self._split_by_heading(content)

            for section_name, section_text in sections:
                if not section_text.strip():
                    continue

                # Clean up text
                text = section_text.strip()

                unit = SourceUnit(
                    source_id=self.source_id,
                    text=text,
                    provenance=Provenance(
                        source_type=SourceType.MARKDOWN,
                        locator=f"{self.source_id}:section={section_name}",
                        source_id=self.source_id,
                    ),
                )
                units.append(unit)

        except Exception as e:
            raise ValueError(f"Failed to parse Markdown {self.file_path}: {e}") from e

        if not units:
            logger.warning(f"Markdown {self.source_id} contains no sections")

        logger.info(f"Markdown adapter ingested {len(units)} sections from {self.source_id}")
        return units

    def _split_by_heading(self, text: str) -> list[tuple[str, str]]:
        """Split markdown by headings (# , ## , ### , etc.).

        Args:
            text: Markdown content.

        Returns:
            List of (heading_name, section_text) tuples.
        """
        # Pattern: lines starting with one or more #, optional space, then heading text
        heading_pattern = r"^(#{1,6})\s+(.+)$"

        sections = []
        current_heading = "introduction"
        current_text = []

        for line in text.split("\n"):
            match = re.match(heading_pattern, line)
            if match:
                # Save previous section
                if current_text or current_heading != "introduction":
                    sections.append((current_heading, "\n".join(current_text)))

                # Start new section
                current_heading = match.group(2).strip()
                current_text = []
            else:
                current_text.append(line)

        # Save final section
        if current_text or current_heading != "introduction":
            sections.append((current_heading, "\n".join(current_text)))

        return sections
