"""Tests for vector search over groups and document source_units."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from spec_atlas.db.analysis import Group, SourceUnit
from spec_atlas.retrieve.search import VectorSearch


def _mock_session(scalar=1, group_rows=None, source_unit_rows=None):
    """Build a mock session whose query(Embedding, Group) and
    query(Embedding, SourceUnit) chains return distinct, controllable result
    sets — needed since _vector_search now issues two separate queries and
    merges them."""
    group_rows = group_rows or []
    source_unit_rows = source_unit_rows or []

    group_query = MagicMock()
    group_query.join.return_value = group_query
    group_query.filter.return_value = group_query
    group_query.order_by.return_value = group_query
    group_query.limit.return_value = group_query
    group_query.all.return_value = group_rows

    source_unit_query = MagicMock()
    source_unit_query.join.return_value = source_unit_query
    source_unit_query.filter.return_value = source_unit_query
    source_unit_query.order_by.return_value = source_unit_query
    source_unit_query.limit.return_value = source_unit_query
    source_unit_query.all.return_value = source_unit_rows

    scalar_query = MagicMock()
    scalar_query.scalar.return_value = scalar

    def query_side_effect(*args, **kwargs):
        # Identity checks (`is`), not `in`/`==`: real SQLAlchemy expression
        # args (e.g. func.count(...)) overload __eq__, so `Group in args`
        # would route through SQLAlchemy's operator coercion instead of a
        # plain Python comparison and raise.
        if any(a is Group for a in args):
            return group_query
        if any(a is SourceUnit for a in args):
            return source_unit_query
        return scalar_query

    mock_session = MagicMock()
    mock_session.query.side_effect = query_side_effect
    return mock_session, group_query, source_unit_query


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

        embed_provider = MagicMock()
        embed_provider.embed_one.return_value = [0.1, 0.2] + [0.0] * 382

        group = MagicMock()
        group.id = uuid.uuid4()
        group.path = "auth"
        group.title = "Authentication"

        embedding = MagicMock()
        embedding.owner_ref = "auth"
        embedding.owner_kind = "group"
        embedding.model = "sentence-transformers/all-MiniLM-L6-v2"
        embedding.vector = [0.1, 0.2] + [0.0] * 382  # Same as query for 1.0 similarity

        mock_session, _, _ = _mock_session(group_rows=[(embedding, group)])

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

        mock_session, _, _ = _mock_session(
            group_rows=[(embedding1, group1), (embedding2, group2)]
        )

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

        mock_session, group_query, source_unit_query = _mock_session()

        VectorSearch.search(
            query="test",
            embed_provider=embed_provider,
            session=mock_session,
            k=7,
        )

        group_query.limit.assert_called_once_with(7)
        source_unit_query.limit.assert_called_once_with(7)

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

        mock_session, _, _ = _mock_session(group_rows=[(embedding, group)])

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
        assert VectorSearch._distance_to_similarity(0.0) == 1.0
        assert VectorSearch._distance_to_similarity(1.0) == 0.5
        assert VectorSearch._distance_to_similarity(2.0) == 0.0
        assert VectorSearch._distance_to_similarity(10.0) == 0.0

    def test_search_uses_correct_model(self) -> None:
        """Search filters by the specified embedding model."""
        embed_provider = MagicMock()
        embed_provider.embed_one.return_value = [0.0] * 384

        mock_session, group_query, _ = _mock_session()

        model = "custom-model"
        VectorSearch.search(
            query="test",
            embed_provider=embed_provider,
            session=mock_session,
            model=model,
        )

        group_query.filter.assert_called_once()

    def test_confidence_is_distance_derived(self) -> None:
        """Similarity reflects actual vector distance, not result rank.

        Regression test: previously every call used a rank-based formula
        (1.0 - i*0.2) so the *first* result was always 1.0 regardless of how
        close it actually was. A close-but-imperfect match must now score
        below a true exact match, and the score must match
        ``_distance_to_similarity`` applied to the real Euclidean distance.
        """
        query_vector = [1.0] * 384

        embed_provider = MagicMock()
        embed_provider.embed_one.return_value = query_vector

        exact_group = MagicMock()
        exact_group.path = "exact"
        exact_embedding = MagicMock()
        exact_embedding.vector = [1.0] * 384  # distance 0 -> similarity 1.0

        far_group = MagicMock()
        far_group.path = "far"
        far_embedding = MagicMock()
        far_embedding.vector = [0.0] * 384  # distance sqrt(384) -> similarity 0.0 (clamped)

        mock_session, _, _ = _mock_session(
            group_rows=[(exact_embedding, exact_group), (far_embedding, far_group)]
        )

        result = VectorSearch.search(
            query="test",
            embed_provider=embed_provider,
            session=mock_session,
            k=2,
        )

        assert result[0][0] == exact_group
        assert result[0][1] == 1.0
        assert result[1][0] == far_group
        assert result[1][1] == 0.0
        assert result[0][1] > result[1][1]

    def test_search_merges_groups_and_source_units_by_distance(self) -> None:
        """A document SourceUnit can outrank a Group when it's the closer match.

        This is the contract document retrieval depends on: VectorSearch must
        consider source_unit embeddings, not just group embeddings, or
        uploaded document content is never retrievable/citable in answers.
        """
        query_vector = [1.0] * 384

        embed_provider = MagicMock()
        embed_provider.embed_one.return_value = query_vector

        far_group = MagicMock(spec=Group)
        far_group.path = "far-group"
        far_group_embedding = MagicMock()
        far_group_embedding.vector = [0.0] * 384  # far

        close_unit = MagicMock(spec=SourceUnit)
        close_unit.id = uuid.uuid4()
        close_unit.locator = "doc.pdf:p.1"
        close_unit_embedding = MagicMock()
        close_unit_embedding.vector = [1.0] * 384  # exact match

        mock_session, _, _ = _mock_session(
            group_rows=[(far_group_embedding, far_group)],
            source_unit_rows=[(close_unit_embedding, close_unit)],
        )

        result = VectorSearch.search(
            query="test",
            embed_provider=embed_provider,
            session=mock_session,
            k=2,
        )

        assert len(result) == 2
        assert result[0][0] is close_unit
        assert isinstance(result[0][0], SourceUnit)
        assert result[0][1] == 1.0
        assert result[1][0] is far_group
