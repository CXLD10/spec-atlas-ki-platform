"""Spec DB models (SQLAlchemy 2.0).

The Spec DB is **durable, per-user, versioned**: L2 specs and the L3 spec graph.
It is kept separate from the Analysis DB; references to analysis entities are by
value (loose ``repo`` / ``component_ref`` strings), never foreign keys. See
DATA-MODEL.md.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SPEC_STATUSES = ("draft", "verified", "stale")
SPEC_EDGE_KINDS = ("depends-on", "part-of", "uses")


class SpecBase(DeclarativeBase):
    """Declarative base / metadata for the Spec DB."""


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Spec(SpecBase):
    """A versioned, immutable spec for an area. Current = valid_to IS NULL."""

    __tablename__ = "specs"
    __table_args__ = (
        UniqueConstraint("user_id", "repo", "component_ref", "version", name="uq_specs_version"),
        CheckConstraint("status IN ('draft','verified','stale')", name="ck_specs_status"),
        Index("ix_specs_lookup", "user_id", "repo", "component_ref"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    repo: Mapped[str] = mapped_column(String, nullable=False)  # loose ref
    component_ref: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)  # monotonic per area
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    # MutableDict/MutableList: plain JSONB columns don't track in-place
    # mutation (e.g. spec.content["_verification_metadata"] = {...} in
    # SpecStore.verify_spec) once the row is persistent — no dirty flag, no
    # UPDATE on commit. Same class of bug as Group.member_node_ids; wrapped
    # here so verification metadata actually survives commit.
    content: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSONB), nullable=False)
    # list of {file_path, start_line, end_line}
    provenance: Mapped[list] = mapped_column(
        MutableList.as_mutable(JSONB), nullable=False, default=list
    )
    source_fingerprint: Mapped[str | None] = mapped_column(Text, nullable=True)
    staleness_detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SpecEdge(SpecBase):
    """L3 spec-graph edge — derived from a real L1 code edge, never an AI guess."""

    __tablename__ = "spec_edges"
    __table_args__ = (
        CheckConstraint("kind IN ('depends-on','part-of','uses')", name="ck_spec_edges_kind"),
        Index("ix_spec_edges_src", "user_id", "repo", "src_component_ref"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    repo: Mapped[str] = mapped_column(String, nullable=False)
    src_component_ref: Mapped[str] = mapped_column(String, nullable=False)
    dst_component_ref: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    derived_from: Mapped[str] = mapped_column(String, nullable=False)  # the L1 edge kind
