"""Embedding pipeline: batch embed groups and specs into pgvector."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Embedding, Group, Repo
from spec_atlas.db.spec import Spec
from spec_atlas.embed.base import EmbeddingProvider

if TYPE_CHECKING:
    pass

# Model ID for the embedding provider
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingPipeline:
    """Batch embed groups and specs into pgvector."""

    @staticmethod
    def embed_groups(
        repo_id: uuid.UUID,
        groups: list[Group],
        embed_provider: EmbeddingProvider,
        session: Session,
    ) -> list[Embedding]:
        """Batch embed group summaries and store in DB.

        Args:
            repo_id: Repository ID.
            groups: List of Group objects (must have summary_md).
            embed_provider: Embedding provider.
            session: Analysis DB session.

        Returns:
            List of persisted Embedding objects.
        """
        if not groups:
            return []

        # Collect texts: use summary_md for each group
        texts = []
        group_paths = []
        for group in groups:
            if group.summary_md:
                texts.append(group.summary_md)
                group_paths.append(group.path)

        if not texts:
            return []

        # Batch embed
        vectors = embed_provider.embed(texts)

        # Create Embedding rows
        embeddings = []
        for path, vector in zip(group_paths, vectors, strict=True):
            embedding = Embedding(
                owner_kind="group",
                owner_ref=path,
                model=DEFAULT_MODEL,
                repo_id=repo_id,
                vector=vector,
            )
            embeddings.append(embedding)
            session.add(embedding)

        session.commit()
        return embeddings

    @staticmethod
    def embed_specs(
        repo_id: uuid.UUID,
        specs: list[Spec],
        embed_provider: EmbeddingProvider,
        session: Session,
    ) -> list[Embedding]:
        """Batch embed spec purpose + content preview and store in DB.

        Args:
            repo_id: Repository ID.
            specs: List of current Spec objects (valid_to is None).
            embed_provider: Embedding provider.
            session: Analysis DB session.

        Returns:
            List of persisted Embedding objects.
        """
        if not specs:
            return []

        # Collect texts: use spec purpose + preview of content
        texts = []
        spec_refs = []
        for spec in specs:
            content = spec.content or {}
            purpose = content.get("purpose", "")

            # Preview: up to 100 words from the content
            content_text = content.get("dependencies", [])
            if isinstance(content_text, list):
                content_preview = " ".join(str(c) for c in content_text[:20])
            else:
                content_preview = str(content_text)[:200]

            # Combine purpose and preview
            text = f"{purpose}. {content_preview}".strip()

            if text:
                texts.append(text)
                spec_refs.append(f"{spec.component_ref}@{spec.version}")

        if not texts:
            return []

        # Batch embed
        vectors = embed_provider.embed(texts)

        # Create Embedding rows
        embeddings = []
        for spec_ref, vector in zip(spec_refs, vectors, strict=True):
            embedding = Embedding(
                owner_kind="spec",
                owner_ref=spec_ref,
                model=DEFAULT_MODEL,
                repo_id=repo_id,
                vector=vector,
            )
            embeddings.append(embedding)
            session.add(embedding)

        session.commit()
        return embeddings

    @staticmethod
    def embed_and_store(
        repo_id: uuid.UUID,
        user_id: str,
        analysis_session: Session,
        spec_session: Session,
        embed_provider: EmbeddingProvider,
    ) -> tuple[int, int]:
        """Orchestrate embedding: fetch groups + specs, embed, store.

        Args:
            repo_id: Repository ID.
            user_id: User ID (for spec lookup).
            analysis_session: Analysis DB session.
            spec_session: Spec DB session.
            embed_provider: Embedding provider.

        Returns:
            Tuple of (groups_embedded, specs_embedded).
        """
        # Fetch all groups for the repo
        groups = analysis_session.query(Group).filter(Group.repo_id == repo_id).all()

        # Fetch the repo to get its name
        repo = analysis_session.query(Repo).filter(Repo.id == repo_id).first()
        if not repo:
            raise ValueError(f"Repo {repo_id} not found")

        # Fetch all current specs for the repo
        specs = (
            spec_session.query(Spec)
            .filter(Spec.session_id == user_id, Spec.repo == repo.name, Spec.valid_to.is_(None))
            .all()
        )

        # Embed groups
        group_embeddings = EmbeddingPipeline.embed_groups(
            repo_id, groups, embed_provider, analysis_session
        )

        # Embed specs
        spec_embeddings = EmbeddingPipeline.embed_specs(
            repo_id, specs, embed_provider, analysis_session
        )

        return len(group_embeddings), len(spec_embeddings)
