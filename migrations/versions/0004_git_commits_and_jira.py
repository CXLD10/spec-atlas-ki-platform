"""repos.recent_commits + source_units 'jira' type (Phase 3)

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-23

Analysis DB only:
- repos.recent_commits (JSONB, nullable) — git log harvested at ingest time;
  powers GET /api/git/history without requiring the ephemeral clone.
- Extends source_units.ck_source_units_type to include 'jira' so Jira issues
  can be indexed as SourceUnits (Phase 3 real Jira import).

Every step is existence-checked before running (same idempotency contract as 0003).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004"
down_revision: str | None = "0003"
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

    # 1. Add repos.recent_commits JSONB column
    if not _has_column(inspector, "repos", "recent_commits"):
        op.add_column("repos", sa.Column("recent_commits", JSONB(), nullable=True))

    # 2. Widen source_units.ck_source_units_type to include 'jira'
    if _has_check_constraint(inspector, "source_units", "ck_source_units_type"):
        op.drop_constraint("ck_source_units_type", "source_units", type_="check")
    op.create_check_constraint(
        "ck_source_units_type",
        "source_units",
        "source_type IN ('pdf','excel','markdown','jira')",
    )


def downgrade_analysis() -> None:
    # Re-imposing the stricter 3-value constraint would fail outright if any
    # 'jira' rows exist (CheckViolation on ADD CONSTRAINT) — downgrading this
    # migration means reverting the capability that created them, so they go
    # too. Analysis DB is documented as rebuildable/disposable (DATA-MODEL.md),
    # so this is consistent with the rest of this DB's downgrade semantics,
    # not a special case. embeddings.owner_ref is a loose text reference (no
    # FK — it also points at Group.path/Spec refs), so clean those up too.
    op.execute(
        "DELETE FROM embeddings WHERE owner_kind = 'source_unit' AND owner_ref IN "
        "(SELECT id::text FROM source_units WHERE source_type = 'jira')"
    )
    op.execute("DELETE FROM source_units WHERE source_type = 'jira'")

    op.drop_constraint("ck_source_units_type", "source_units", type_="check")
    op.create_check_constraint(
        "ck_source_units_type",
        "source_units",
        "source_type IN ('pdf','excel','markdown')",
    )
    # recent_commits column is left in place on downgrade (data-safe).


def upgrade_spec() -> None:
    pass


def downgrade_spec() -> None:
    pass
