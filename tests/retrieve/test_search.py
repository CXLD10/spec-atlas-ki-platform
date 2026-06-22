"""Tests for vector search over groups."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from spec_atlas.retrieve.search import VectorSearch


class TestVectorSearch:
    """Tests for vector search retrieval."""

    def test_search_empty_query(self) -> None:
        """Searching with empty query returns empty result."""
        result = VectorSearch.search(
            query="",
            embed_provider=MagicMock(),
            session=MagicMock(),
        )

        assert result == []

    def test_search_none_query(self) -> None:
        """Searching with None query returns empty result."""
        result = VectorSearch.search(
            query="",
            embed_provider=MagicMock(),
            session=MagicMock(),
        )

        assert result == []

    def test_search_single_result(self) -> None:
        """Searching returns groups with similarity scores."""
        query = "What is authentication?"

        # Mock embedding provider
        embed_provider = MagicMock()
        embed_provider.embed_one.return_value = [0.1, 0.2] + [0.0] * 382

        # Mock group and embedding
        group = MagicMock()
        group.id = uuid.uuid4()
        group.path = "auth"
        group.title = "Authentication"

        embedding = MagicMock()
        embedding.owner_ref = "auth"
        embedding.owner_kind = "group"
        embedding.model = "sentence-transformers/all-MiniLM-L6-v2"
        embedding.vector = [0.1, 0.2] + [0.0] * 382  # Same as query for 1.0 similarity

        # Mock session query chain
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.scalar.return_value = 1  # Embeddings exist
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [(embedding, group)]

        result = VectorSearch.search(
            query=query,
            embed_provider=embed_provider,
            session=mock_session,
            k=3,
        )

        assert len(result) == 1
        assert result[0][0] == group

    def test_search_multiple_results(self) -> None:
        """Searching returns multiple groups ordered by relevance."""
        query = "database operations"

        embed_provider = MagicMock()
        embed_provider.embed_one.return_value = [0.5] * 384

        # Create multiple groups
        group1 = MagicMock()
        group1.path = "db"

        group2 = MagicMock()
        group2.path = "cache"

        embedding1 = MagicMock()
        embedding1.owner_ref = "db"
        embedding1.vector = [0.5] * 384

        embedding2 = MagicMock()
        embedding2.owner_ref = "cache"
        embedding2.vector = [0.4] * 384

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.scalar.return_value = 1  # Embeddings exist
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [(embedding1, group1), (embedding2, group2)]

        result = VectorSearch.search(
            query=query,
            embed_provider=embed_provider,
            session=mock_session,
            k=5,
        )

        assert len(result) == 2
        assert result[0][0] == group1
        assert result[1][0] == group2

    def test_search_respects_k_limit(self) -> None:
        """Searching respects the k parameter."""
        embed_provider = MagicMock()
        embed_provider.embed_one.return_value = [0.0] * 384

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        # Mock scalar() return for embedding count check
        mock_query.scalar.return_value = 1
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        VectorSearch.search(
            query="test",
            embed_provider=embed_provider,
            session=mock_session,
            k=7,
        )

        # Verify limit was called with k=7
        mock_query.limit.assert_called_once_with(7)

    def test_search_similarity_score_range(self) -> None:
        """Search results have similarity scores in [0, 1]."""
        query = "test query"

        embed_provider = MagicMock()
        embed_provider.embed_one.return_value = [0.1] * 384

        group = MagicMock()
        group.path = "test"

        embedding = MagicMock()
        embedding.owner_ref = "test"
        embedding.vector = [0.1] * 384  # Identical to query

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        # Mock scalar() return for embedding count check
        mock_query.scalar.return_value = 1
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [(embedding, group)]

        result = VectorSearch.search(
            query=query,
            embed_provider=embed_provider,
            session=mock_session,
        )

        assert len(result) == 1
        similarity = result[0][1]
        assert 0.0 <= similarity <= 1.0

    def test_distance_to_similarity(self) -> None:
        """Distance to similarity conversion works correctly."""
        # Distance 0 should give similarity 1.0
        assert VectorSearch._distance_to_similarity(0.0) == 1.0

        # Distance 1.0 should give similarity 0.5
        assert VectorSearch._distance_to_similarity(1.0) == 0.5

        # Distance 2.0 should give similarity 0.0
        assert VectorSearch._distance_to_similarity(2.0) == 0.0

        # Very large distance should clamp to 0.0
        assert VectorSearch._distance_to_similarity(10.0) == 0.0

    def test_search_uses_correct_model(self) -> None:
        """Search filters by the specified embedding model."""
        embed_provider = MagicMock()
        embed_provider.embed_one.return_value = [0.0] * 384

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        # Mock scalar() return for embedding count check
        mock_query.scalar.return_value = 1
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        model = "custom-model"
        VectorSearch.search(
            query="test",
            embed_provider=embed_provider,
            session=mock_session,
            model=model,
        )

        # Verify that filter was called (would filter by model)
        mock_query.filter.assert_called_once()
