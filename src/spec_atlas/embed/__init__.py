"""Embedding providers — interface, local default (fastembed), and offline fake.

Use :func:`get_embedding_provider` to obtain the provider selected by configuration
(``EMBED_PROVIDER``); callers depend only on :class:`EmbeddingProvider`.
"""

from __future__ import annotations

from spec_atlas.config import Settings, get_settings

from .base import EmbeddingProvider
from .fake import FakeEmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "FakeEmbeddingProvider",
    "get_embedding_provider",
]


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    """Return the configured embedding provider (``fake`` or ``fastembed``)."""
    s = settings or get_settings()
    if s.embed_provider == "fake":
        return FakeEmbeddingProvider(dim=s.embed_dim)
    if s.embed_provider == "fastembed":
        # Imported lazily so the fake path never imports fastembed/onnxruntime.
        from .fastembed_provider import FastembedEmbeddingProvider

        return FastembedEmbeddingProvider(model=s.embed_model, dim=s.embed_dim)
    raise ValueError(f"Unknown EMBED_PROVIDER: {s.embed_provider!r}")
