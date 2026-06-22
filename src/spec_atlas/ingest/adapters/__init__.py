"""Source adapters for multi-format ingestion."""

from __future__ import annotations

from spec_atlas.ingest.adapters.base import SourceAdapter
from spec_atlas.ingest.adapters.pdf import PDFAdapter

__all__ = ["SourceAdapter", "PDFAdapter"]
