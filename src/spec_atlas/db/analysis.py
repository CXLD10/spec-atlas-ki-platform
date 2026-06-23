"""Analysis DB models (SQLAlchemy 2.0).

The Analysis DB is the **rebuildable** index: the L1 code graph (``repos``,
``files``, ``nodes``, ``edges``), the L4 ``groups`` tree, and ``embeddings``
(pgvector). It is disposable and re-derivable from source. See DATA-MODEL.md.

Cross-DB references to the Spec DB are by value (text refs), never foreign keys.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

EMBED_DIM = 384  # must match Settings.embed_dim and embeddings.vector(N)

NODE_KINDS = ("module", "class", "function", "method")
EDGE_KINDS = ("imports", "calls", "inherits", "defines")
EMBED_OWNER_KINDS = ("group", "spec")


class AnalysisBase(DeclarativeBase):
    """Declarative base / metadata for the Analysis DB."""


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Repo(AnalysisBase):
    __tablename__ = "repos"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)  # local path or URL
    default_branch: Mapped[str | None] = mapped_column(String, nullable=True)
    indexed_commit: Mapped[str | None] = mapped_column(String, nullable=True)  # sha
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class File(AnalysisBase):
    __tablename__ = "files"
    __table_args__ = (UniqueConstraint("repo_id", "path", name="uq_files_repo_path"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repos.id", ondelete="CASCADE"), nullable=False
    )
    path: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    loc: Mapped[int] = mapped_column(Integer, nullable=False)


class Node(AnalysisBase):
    """L1 symbol. Stable identity: (repo_id, language, qualified_name, kind)."""

    __tablename__ = "nodes"
    __table_args__ = (
        UniqueConstraint("repo_id", "language", "qualified_name", "kind", name="uq_nodes_identity"),
        CheckConstraint("kind IN ('module','class','function','method')", name="ck_nodes_kind"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repos.id", ondelete="CASCADE"), nullable=False
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False
    )
    language: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    qualified_name: Mapped[str] = mapped_column(String, nullable=False)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    docstring: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)


class Edge(AnalysisBase):
    __tablename__ = "edges"
    __table_args__ = (
        CheckConstraint("kind IN ('imports','calls','inherits','defines')", name="ck_edges_kind"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_edges_confidence"),
        Index("ix_edges_repo_src", "repo_id", "src_node_id"),
        Index("ix_edges_repo_dst", "repo_id", "dst_node_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repos.id", ondelete="CASCADE"), nullable=False
    )
    src_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False
    )
    dst_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class Group(AnalysisBase):
    """L4 group.md tree node (self-referential parent/child)."""

    __tablename__ = "groups"
    __table_args__ = (Index("ix_groups_repo_parent", "repo_id", "parent_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repos.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=True
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. auth/tokens
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary_md: Mapped[str | None] = mapped_column(Text, nullable=True)  # the group.md page
    # MutableList: plain ARRAY columns don't track in-place .append()/.remove()
    # on an already-persistent row (no dirty flag => no UPDATE emitted on
    # commit) — this silently dropped every member_node_ids/member_spec_refs
    # mutation made after the owning Group row was flushed (e.g. clustering's
    # node-to-group assignment, which runs right after an FK-establishing
    # flush). MutableList.as_mutable wraps the column so in-place edits are
    # detected like any other attribute change.
    member_node_ids: Mapped[list[uuid.UUID]] = mapped_column(
        MutableList.as_mutable(ARRAY(UUID(as_uuid=True))), nullable=False, default=list
    )
    # component_refs into the Spec DB (by value, not FK)
    member_spec_refs: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(ARRAY(Text)), nullable=False, default=list
    )
    source_fingerprint: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Embedding(AnalysisBase):
    """Vectors for groups (primary retrieval) and specs (direct lookup).

    Composite PK (owner_kind, owner_ref, model). No vectors on raw nodes (ADR-0001 D3).
    """

    __tablename__ = "embeddings"
    __table_args__ = (
        CheckConstraint("owner_kind IN ('group','spec')", name="ck_embeddings_owner_kind"),
    )

    owner_kind: Mapped[str] = mapped_column(String, primary_key=True)
    owner_ref: Mapped[str] = mapped_column(Text, primary_key=True)
    model: Mapped[str] = mapped_column(String, primary_key=True)
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repos.id", ondelete="CASCADE"), nullable=False
    )
    vector: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM), nullable=False)


class IngestJob(AnalysisBase):
    """Ingest job tracking (ephemeral; can be cleaned up after completion).

    Tracks async ingest jobs: repo_url, status (queued/in_progress/done/error),
    progress percentage, and optional error message.
    """

    __tablename__ = "ingest_jobs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    repo_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="queued"
    )  # queued, in_progress, done, error
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
