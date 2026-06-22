"""Default embedding provider — local fastembed (CPU, zero cost).

Wraps ``fastembed.TextEmbedding`` with ``BAAI/bge-small-en-v1.5`` (384-dim). The model
is loaded lazily on first use; the first run downloads/caches it (the only time network
is needed). Never used in CI — CI uses the fake (INTEGRATIONS.md §4, NFR: $0)."""

from __future__ import annotations

from collections.abc import Sequence

from .base import EmbeddingProvider

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_DIM = 384


class FastembedEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str = DEFAULT_MODEL, dim: int = DEFAULT_DIM) -> None:
        self._model_name = model
        self._dim = dim
        self._model = None  # lazy; avoids importing/downloading at construction time

    @property
    def dim(self) -> int:
        return self._dim

    def _ensure_model(self):
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self._model_name)
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._ensure_model()
        # fastembed yields numpy arrays; normalize to plain Python lists.
        return [list(map(float, vec)) for vec in model.embed(list(texts))]
