"""Adapter for Git repositories and local code."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from spec_atlas.ingest.adapters.base import SourceAdapter
from spec_atlas.ingest.source_unit import Provenance, SourceType, SourceUnit

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class CodeAdapter(SourceAdapter):
    """Adapter for Git repositories and local code."""

    def __init__(self, source_id: str, repo_path: str, file_paths: list[str]):
        """Initialize code adapter.

        Args:
            source_id: Repository identifier (URL or path).
            repo_path: Absolute path to the repository root.
            file_paths: List of relative file paths from repo root.
        """
        super().__init__(source_id)
        self.repo_path = repo_path
        self.file_paths = file_paths

    async def ingest(self) -> list[SourceUnit]:
        """Read all code files and emit SourceUnits.

        Returns:
            List of SourceUnit, one per file in the repository.
        """
        units = []
        repo_root = Path(self.repo_path)

        for file_rel_path in self.file_paths:
            file_path = repo_root / file_rel_path

            # Skip directories and non-readable files
            if not file_path.is_file():
                continue

            try:
                with open(file_path, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError as e:
                logger.warning(f"Failed to read {file_rel_path}: {e}")
                continue

            # Create SourceUnit with code provenance
            unit = SourceUnit(
                source_id=self.source_id,
                text=text,
                provenance=Provenance(
                    source_type=SourceType.CODE,
                    locator=f"{file_rel_path}:0",  # Refined during parsing
                    source_id=self.source_id,
                ),
            )
            units.append(unit)

        logger.info(f"Code adapter ingested {len(units)} files from {self.source_id}")
        return units
