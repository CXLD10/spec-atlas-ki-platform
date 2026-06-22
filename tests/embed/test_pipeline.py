"""Tests for embedding pipeline."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from spec_atlas.embed.pipeline import EmbeddingPipeline


class TestEmbeddingPipeline:
    """Tests for batch embedding groups and specs."""

    def test_embed_groups_empty_list(self) -> None:
        """Embedding empty group list returns empty."""
        result = EmbeddingPipeline.embed_groups(
            repo_id=uuid.uuid4(),
            groups=[],
            embed_provider=MagicMock(),
            session=MagicMock(),
        )

        assert result == []

    def test_embed_groups_without_summary(self) -> None:
        """Groups without summary_md are skipped."""
        group = MagicMock()
        group.path = "auth"
        group.summary_md = None

        result = EmbeddingPipeline.embed_groups(
            repo_id=uuid.uuid4(),
            groups=[group],
            embed_provider=MagicMock(),
            session=MagicMock(),
        )

        assert result == []

    def test_embed_groups_single_group(self) -> None:
        """Embedding single group creates Embedding row."""
        repo_id = uuid.uuid4()
        group = MagicMock()
        group.path = "auth"
        group.summary_md = "Authentication module"

        embed_provider = MagicMock()
        embed_provider.embed.return_value = [
            [0.1, 0.2, 0.3] + [0.0] * 381  # 384 dims
        ]

        mock_session = MagicMock()

        result = EmbeddingPipeline.embed_groups(
            repo_id=repo_id,
            groups=[group],
            embed_provider=embed_provider,
            session=mock_session,
        )

        assert len(result) == 1
        assert result[0].owner_kind == "group"
        assert result[0].owner_ref == "auth"
        assert len(result[0].vector) == 384  # 384 dims

    def test_embed_groups_multiple_groups(self) -> None:
        """Embedding multiple groups batch embeds all."""
        repo_id = uuid.uuid4()

        group1 = MagicMock()
        group1.path = "auth"
        group1.summary_md = "Authentication"

        group2 = MagicMock()
        group2.path = "api"
        group2.summary_md = "API layer"

        embed_provider = MagicMock()
        embed_provider.embed.return_value = [
            [0.1, 0.2] + [0.0] * 382,
            [0.3, 0.4] + [0.0] * 382,
        ]

        mock_session = MagicMock()

        result = EmbeddingPipeline.embed_groups(
            repo_id=repo_id,
            groups=[group1, group2],
            embed_provider=embed_provider,
            session=mock_session,
        )

        assert len(result) == 2
        assert result[0].owner_ref == "auth"
        assert result[1].owner_ref == "api"

    def test_embed_specs_empty_list(self) -> None:
        """Embedding empty spec list returns empty."""
        result = EmbeddingPipeline.embed_specs(
            repo_id=uuid.uuid4(),
            specs=[],
            embed_provider=MagicMock(),
            session=MagicMock(),
        )

        assert result == []

    def test_embed_specs_single_spec(self) -> None:
        """Embedding single spec creates Embedding row."""
        repo_id = uuid.uuid4()

        spec = MagicMock()
        spec.component_ref = "UserService"
        spec.version = 1
        spec.content = {
            "purpose": "Manages user accounts",
            "dependencies": ["auth", "db"],
        }

        embed_provider = MagicMock()
        embed_provider.embed.return_value = [[0.1, 0.2] + [0.0] * 382]

        mock_session = MagicMock()

        result = EmbeddingPipeline.embed_specs(
            repo_id=repo_id,
            specs=[spec],
            embed_provider=embed_provider,
            session=mock_session,
        )

        assert len(result) == 1
        assert result[0].owner_kind == "spec"
        assert result[0].owner_ref == "UserService@1"

    def test_embed_specs_with_empty_content(self) -> None:
        """Specs with empty content dict are handled gracefully."""
        repo_id = uuid.uuid4()

        spec = MagicMock()
        spec.component_ref = "Empty"
        spec.version = 1
        spec.content = {}

        embed_provider = MagicMock()
        # Even with empty content, we may produce a minimal text; mock returns vectors
        embed_provider.embed.return_value = [[0.0] * 384]

        mock_session = MagicMock()

        result = EmbeddingPipeline.embed_specs(
            repo_id=repo_id,
            specs=[spec],
            embed_provider=embed_provider,
            session=mock_session,
        )

        # May have an embedding if text is non-empty after joining
        assert isinstance(result, list)

    def test_embed_specs_batch_embedding(self) -> None:
        """Multiple specs are batch embedded."""
        repo_id = uuid.uuid4()

        spec1 = MagicMock()
        spec1.component_ref = "Service1"
        spec1.version = 1
        spec1.content = {"purpose": "First service"}

        spec2 = MagicMock()
        spec2.component_ref = "Service2"
        spec2.version = 1
        spec2.content = {"purpose": "Second service"}

        embed_provider = MagicMock()
        embed_provider.embed.return_value = [
            [0.1] * 384,
            [0.2] * 384,
        ]

        mock_session = MagicMock()

        result = EmbeddingPipeline.embed_specs(
            repo_id=repo_id,
            specs=[spec1, spec2],
            embed_provider=embed_provider,
            session=mock_session,
        )

        assert len(result) == 2
        embed_provider.embed.assert_called_once()
        # Check that both texts were passed to embed
        call_args = embed_provider.embed.call_args[0][0]
        assert len(call_args) == 2

    def test_embed_and_store_orchestrates(self) -> None:
        """embed_and_store orchestrates groups + specs embedding."""
        repo_id = uuid.uuid4()
        user_id = "test_user"

        # Mock repo
        repo = MagicMock()
        repo.id = repo_id
        repo.name = "test_repo"

        # Mock group
        group = MagicMock()
        group.path = "auth"
        group.summary_md = "Auth module"

        # Mock spec
        spec = MagicMock()
        spec.user_id = user_id
        spec.repo = "test_repo"
        spec.component_ref = "AuthService"
        spec.version = 1
        spec.valid_to = None
        spec.content = {"purpose": "Handles authentication"}

        # Mock sessions
        analysis_session = MagicMock()
        analysis_session.query.return_value.filter.return_value.first.return_value = repo
        analysis_session.query.return_value.filter.return_value.all.return_value = [group]

        spec_session = MagicMock()
        spec_session.query.return_value.filter.return_value.all.return_value = [spec]

        # Mock provider - return exactly 2 vectors (1 group + 1 spec)
        embed_provider = MagicMock()
        call_count = [0]

        def mock_embed(texts):
            call_count[0] += 1
            return [[0.1 * i] * 384 for i in range(len(texts))]

        embed_provider.embed.side_effect = mock_embed

        result = EmbeddingPipeline.embed_and_store(
            repo_id=repo_id,
            user_id=user_id,
            analysis_session=analysis_session,
            spec_session=spec_session,
            embed_provider=embed_provider,
        )

        # Should return (groups_count, specs_count)
        assert result == (1, 1)

    def test_embedding_stores_vector(self) -> None:
        """Embeddings store correct vector in DB."""
        repo_id = uuid.uuid4()

        group = MagicMock()
        group.path = "core"
        group.summary_md = "Core module"

        vector = [0.1, 0.2, 0.3] + [0.0] * 381

        embed_provider = MagicMock()
        embed_provider.embed.return_value = [vector]

        mock_session = MagicMock()

        result = EmbeddingPipeline.embed_groups(
            repo_id=repo_id,
            groups=[group],
            embed_provider=embed_provider,
            session=mock_session,
        )

        # Check vector is stored
        assert result[0].vector == vector
        assert result[0].repo_id == repo_id
