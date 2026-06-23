"""Vector search over group + document embeddings, or keyword fallback on nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import cast, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Embedding, Group, Node, SourceUnit
from spec_atlas.embed.base import EmbeddingProvider

if TYPE_CHECKING:
    pass


def _euclidean_distance(a: list[float], b: list[float]) -> float:
    """L2 distance between two equal-length vectors (matches pgvector's `<->`)."""
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


class VectorSearch:
    """Search for relevant groups/document units via ANN on embeddings, with
    node-based keyword fallback."""

    @staticmethod
    def search(
        query: str,
        embed_provider: EmbeddingProvider,
        session: Session,
        k: int = 3,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> list[tuple[Group | SourceUnit, float]]:
        """Search for top-K groups/source_units via ANN on embeddings, or
        fallback to node matching.

        Args:
            query: User query string.
            embed_provider: Embedding provider (to embed query).
            session: Analysis DB session.
            k: Number of top results to return (default 3).
            model: Embedding model ID to search over.

        Returns:
            List of (owner, similarity_score) tuples, sorted by score (highest
            first). owner is a Group (code/L4) or SourceUnit (document
            page/row/section) — check with isinstance(). Similarity scores
            are 0-1 (higher = more similar).
        """
        if not query or not query.strip():
            return []

        # Check if we have any embeddings
        embedding_count = session.query(func.count(Embedding.owner_ref)).scalar()
        if embedding_count > 0:
            # Vector search: use embeddings
            return VectorSearch._vector_search(query, embed_provider, session, k, model)
        else:
            # Fallback: keyword search on nodes
            return VectorSearch._node_keyword_search(query, session, k)

    @staticmethod
    def _vector_search(
        query: str,
        embed_provider: EmbeddingProvider,
        session: Session,
        k: int = 3,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> list[tuple[Group | SourceUnit, float]]:
        """Vector search across both group (code) and source_unit (document)
        embeddings, merged into one ranked-by-distance result set."""
        query_vector = embed_provider.embed_one(query)

        group_results = (
            session.query(Embedding, Group)
            .join(Group, (Embedding.owner_ref == Group.path) & (Embedding.owner_kind == "group"))
            .filter(Embedding.model == model)
            .order_by(Embedding.vector.op("<->")(query_vector))
            .limit(k)
            .all()
        )

        source_unit_results = (
            session.query(Embedding, SourceUnit)
            .join(
                SourceUnit,
                (cast(Embedding.owner_ref, UUID(as_uuid=True)) == SourceUnit.id)
                & (Embedding.owner_kind == "source_unit"),
            )
            .filter(Embedding.model == model)
            .order_by(Embedding.vector.op("<->")(query_vector))
            .limit(k)
            .all()
        )

        # Distance is computed from the actual stored vectors (matching the
        # pgvector `<->` L2 metric used in the ORDER BY above), not derived
        # from result rank — then merged across owner types and re-ranked.
        output: list[tuple[Group | SourceUnit, float]] = []
        for embedding, owner in [*group_results, *source_unit_results]:
            distance = _euclidean_distance(query_vector, embedding.vector)
            similarity = VectorSearch._distance_to_similarity(distance)
            output.append((owner, similarity))

        output.sort(key=lambda pair: pair[1], reverse=True)
        return output[:k]

    @staticmethod
    def _node_keyword_search(query: str, session: Session, k: int = 3) -> list[tuple[Group, float]]:
        """Fallback: keyword search on node names when embeddings don't exist."""
        # Extract keywords from query
        keywords = query.lower().split()

        # Search nodes by name (simple substring match)
        nodes = session.query(Node).all()

        # Score nodes based on keyword matches
        scored_nodes = []
        for node in nodes:
            score = 0
            node_name_lower = (node.name or "").lower()
            node_qname_lower = (node.qualified_name or "").lower()

            for keyword in keywords:
                if keyword in node_name_lower:
                    score += 2
                if keyword in node_qname_lower:
                    score += 1

            if score > 0:
                scored_nodes.append((node, score))

        # Sort by score (highest first) and take top k
        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        top_nodes = scored_nodes[:k]

        # Create synthetic groups from top nodes (for compatibility with TreeDescent)
        result = []
        for _i, (node, score) in enumerate(top_nodes):
            # Create a synthetic group from the node
            docstring_str = node.docstring or "(none)"
            synthetic_group = Group(
                id=node.id,
                repo_id=node.repo_id,
                path=node.qualified_name or node.name,
                level=0,
                title=node.name or "unknown",
                parent_id=None,
                member_spec_refs=[],
                summary_md=(
                    f"Symbol: {node.qualified_name or node.name}\nKind: {node.kind}\n"
                    f"Docstring: {docstring_str}"
                ),
            )

            # Normalize score to [0, 1]
            similarity = min(1.0, score / 10.0)
            result.append((synthetic_group, similarity))

        return result

    @staticmethod
    def _distance_to_similarity(distance: float) -> float:
        """Convert pgvector distance to similarity score [0, 1].

        Args:
            distance: Euclidean distance from pgvector.

        Returns:
            Similarity score in [0, 1].
        """
        # For normalized vectors (as from embeddings), distance ranges roughly [0, 2]
        # Map: 0 distance → 1.0 similarity, 2 distance → 0.0 similarity
        return max(0.0, 1.0 - distance / 2.0)
