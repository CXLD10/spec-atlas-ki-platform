"""specs.staleness_detected_at (Phase 5 drift detection)

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-24

Spec DB only:
- specs.staleness_detected_at (DateTime TZ, nullable) — set by DriftDetector
  when a spec's source fingerprint no longer matches the current code. NULL
  means the spec has never been marked stale.

Existence-checked before adding (idempotent, same pattern as 0003/0004).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(engine_name: str) -> None:
    globals()[f"upgrade_{engine_name}"]()


def downgrade(engine_name: str) -> None:
    globals()[f"downgrade_{engine_name}"]()


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade_analysis() -> None:
    pass


def downgrade_analysis() -> None:
    pass


def upgrade_spec() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "specs", "staleness_detected_at"):
        op.add_column(
            "specs",
            sa.Column(
                "staleness_detected_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )


def downgrade_spec() -> None:
    # Column is data-safe to drop (only metadata, not content).
    op.drop_column("specs", "staleness_detected_at")
