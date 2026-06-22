"""Deterministic, offline fake embedding provider.

Maps text → a stable L2-normalized vector via SHA-256, with no network, model
download, or randomness. Same text always yields the same vector; different texts
yield (almost surely) different vectors. Used whenever ``EMBED_PROVIDER=fake`` so
tests and CI run fully offline (testing-standard)."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence

from .base import EmbeddingProvider

DEFAULT_DIM = 384


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dim: int = DEFAULT_DIM) -> None:
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def _vector(self, text: str) -> list[float]:
        values: list[float] = []
        counter = 0
        # Stretch SHA-256 output until we have `dim` floats in [-1, 1).
        while len(values) < self._dim:
            digest = hashlib.sha256(f"{counter}:{text}".encode()).digest()
            for i in range(0, len(digest), 4):
                if len(values) >= self._dim:
                    break
                raw = int.from_bytes(digest[i : i + 4], "big") / 2**32
                values.append(raw * 2.0 - 1.0)
            counter += 1
        # L2-normalize so the fake behaves like real (normalized) embeddings.
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]
