"""Abstract base class for all source adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spec_atlas.ingest.source_unit import SourceUnit


class SourceAdapter(ABC):
    """Abstract base for all source adapters."""

    def __init__(self, source_id: str):
        """Initialize adapter with source identifier.

        Args:
            source_id: Unique identifier for the source (repo URL, file path, etc.)
        """
        self.source_id = source_id

    @abstractmethod
    async def ingest(self) -> list[SourceUnit]:
        """Return a list of SourceUnits from this source.

        Returns:
            List of SourceUnit objects, one per logical unit of content.

        Raises:
            ValueError: If the source is invalid or inaccessible.
            RuntimeError: If ingestion fails.
        """
        pass
