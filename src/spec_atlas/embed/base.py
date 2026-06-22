"""Embedding provider interface.

All embedding access goes through :class:`EmbeddingProvider`; callers never import a
vendor SDK directly (ARCHITECTURE.md cross-cutting contracts). The default is local
(fastembed, zero cost); a deterministic fake makes the whole system testable offline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence


class EmbeddingProvider(ABC):
    """Turn text into fixed-dimension vectors.

    Implementations must be deterministic for a given input and return vectors whose
    length equals :attr:`dim`. ``dim`` must match the ``embeddings.vector(N)`` column
    (DATA-MODEL.md) — 384 for the default bge-small model.
    """

    @property
    @abstractmethod
    def dim(self) -> int:
        """Dimension of every returned vector."""

    @abstractmethod
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of texts → one vector per input, order preserved."""

    def embed_one(self, text: str) -> list[float]:
        """Convenience: embed a single text."""
        return self.embed([text])[0]
