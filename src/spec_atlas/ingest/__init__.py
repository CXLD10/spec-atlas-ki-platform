"""Ingestion pipeline — repo resolver, file inventory, language detection."""

from __future__ import annotations

from .resolver import RepoMetadata, RepoResolver

__all__ = [
    "RepoResolver",
    "RepoMetadata",
]
