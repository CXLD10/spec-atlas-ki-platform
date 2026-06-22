"""Contract tests for the fake embedding provider (offline, deterministic)."""

from __future__ import annotations

import math

from spec_atlas.embed import FakeEmbeddingProvider, get_embedding_provider


def test_dim_is_384_by_default() -> None:
    p = FakeEmbeddingProvider()
    vecs = p.embed(["hello", "world"])
    assert p.dim == 384
    assert all(len(v) == 384 for v in vecs)


def test_deterministic_same_text_same_vector() -> None:
    p = FakeEmbeddingProvider()
    assert p.embed(["auth tokens"]) == p.embed(["auth tokens"])


def test_different_text_different_vector() -> None:
    p = FakeEmbeddingProvider()
    a = p.embed_one("alpha")
    b = p.embed_one("beta")
    assert a != b


def test_vectors_are_l2_normalized() -> None:
    p = FakeEmbeddingProvider()
    v = p.embed_one("normalize me")
    assert math.isclose(math.sqrt(sum(x * x for x in v)), 1.0, rel_tol=1e-9)


def test_batch_order_preserved_and_one_vector_per_input() -> None:
    p = FakeEmbeddingProvider()
    texts = ["a", "b", "c"]
    out = p.embed(texts)
    assert len(out) == len(texts)
    assert out[1] == p.embed_one("b")


def test_custom_dim() -> None:
    p = FakeEmbeddingProvider(dim=16)
    assert len(p.embed_one("x")) == 16


def test_factory_returns_fake_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("EMBED_PROVIDER", "fake")
    from spec_atlas.config import Settings

    provider = get_embedding_provider(Settings(_env_file=None))
    assert isinstance(provider, FakeEmbeddingProvider)
    assert provider.dim == 384
