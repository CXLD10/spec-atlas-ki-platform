"""source_units table + Repo.source_format + embeddings owner_kind (Phase 2)

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-23

Analysis DB only:
- repos.source_format ('git'|'pdf'|'xlsx'|'md') — documents reuse the repos
  table instead of a parallel "documents" table, so existing aggregation
  (embeddings.repo_id FK, /api/sources, group counts) covers them for free.
- source_units table: durable, embeddable, citable PDF page / Excel row /
  Markdown section units (the document analogue of `nodes`).
- embeddings.owner_kind CHECK constraint extended to allow 'source_unit'.

Every step here is existence-checked before running. 0001_initial's
``create_all()`` always reflects the *current* model definitions (it isn't a
historical snapshot), so on a fresh database it already creates
repos.source_format, source_units, and the 3-value owner_kind constraint —
this migration only has real work to do against a database that ran 0001/0002
before those model fields existed.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(engine_name: str) -> None:
    globals()[f"upgrade_{engine_name}"]()


def downgrade(engine_name: str) -> None:
    globals()[f"downgrade_{engine_name}"]()


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspector.get_columns(table))


def _has_check_constraint(inspector: sa.Inspector, table: str, name: str) -> bool:
    return any(c["name"] == name for c in inspector.get_check_constraints(table))


def upgrade_analysis() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "repos", "source_format"):
        op.add_column(
            "repos",
            sa.Column("source_format", sa.String(), nullable=False, server_default="git"),
        )
    if not _has_check_constraint(inspector, "repos", "ck_repos_source_format"):
        op.create_check_constraint(
            "ck_repos_source_format", "repos", "source_format IN ('git','pdf','xlsx','md')"
        )

    from spec_atlas.db.analysis import SourceUnit

    SourceUnit.__table__.create(bind, checkfirst=True)

    # Re-inspect: the check-constraint list above was captured before the
    # possible add_column/create_check_constraint calls.
    inspector = sa.inspect(bind)
    existing_check = next(
        (
            c
            for c in inspector.get_check_constraints("embeddings")
            if c["name"] == "ck_embeddings_owner_kind"
        ),
        None,
    )
    if existing_check and "source_unit" not in existing_check.get("sqltext", ""):
        op.drop_constraint("ck_embeddings_owner_kind", "embeddings", type_="check")
        existing_check = None
    if not existing_check:
        op.create_check_constraint(
            "ck_embeddings_owner_kind",
            "embeddings",
            "owner_kind IN ('group','spec','source_unit')",
        )


def downgrade_analysis() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_check_constraint(inspector, "embeddings", "ck_embeddings_owner_kind"):
        op.drop_constraint("ck_embeddings_owner_kind", "embeddings", type_="check")
        op.create_check_constraint(
            "ck_embeddings_owner_kind", "embeddings", "owner_kind IN ('group','spec')"
        )

    from spec_atlas.db.analysis import SourceUnit

    SourceUnit.__table__.drop(bind, checkfirst=True)

    if _has_check_constraint(inspector, "repos", "ck_repos_source_format"):
        op.drop_constraint("ck_repos_source_format", "repos", type_="check")
    if _has_column(inspector, "repos", "source_format"):
        op.drop_column("repos", "source_format")


def upgrade_spec() -> None:
    """No-op for Spec DB (source_units belong to Analysis DB only)."""
    pass


def downgrade_spec() -> None:
    """No-op for Spec DB."""
    pass
