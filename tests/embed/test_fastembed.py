"""Contract test for the default (fastembed) embedding provider.

Skipped when the model can't be loaded (uncached + offline), so CI stays green and
free. When it does run, it asserts the real provider returns 384-dim vectors and is
deterministic — the contract every caller relies on."""

from __future__ import annotations

import pytest

from spec_atlas.embed.fastembed_provider import FastembedEmbeddingProvider


@pytest.fixture(scope="module")
def provider() -> FastembedEmbeddingProvider:
    p = FastembedEmbeddingProvider()
    try:
        p._ensure_model()  # loads/downloads the model; needs network if uncached
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"fastembed model unavailable offline: {exc}")
    return p


def test_default_embeddings_are_384_dim(provider: FastembedEmbeddingProvider) -> None:
    vecs = provider.embed(["how does auth work", "what calls mint()"])
    assert provider.dim == 384
    assert all(len(v) == 384 for v in vecs)
    assert all(isinstance(x, float) for x in vecs[0])


def test_default_is_deterministic(provider: FastembedEmbeddingProvider) -> None:
    assert provider.embed(["stable text"]) == provider.embed(["stable text"])
