"""Add ETA tracking fields to ingest_jobs (Phase 6 ETA display)

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-24

Analysis DB only:
- ingest_jobs.current_phase (String, nullable) — name of current phase (resolve, inventory, etc.)
- ingest_jobs.phase_start_time (DateTime TZ, nullable) — when the current phase started
- ingest_jobs.phase_durations (JSONB, nullable) — {phase_name: seconds_elapsed}
- ingest_jobs.estimated_completion (DateTime TZ, nullable) — estimated job completion time

These fields enable ETA calculation and learning-based improvements.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(engine_name: str) -> None:
    globals()[f"upgrade_{engine_name}"]()


def downgrade(engine_name: str) -> None:
    globals()[f"downgrade_{engine_name}"]()


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade_analysis() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Add phase tracking columns to ingest_jobs
    if not _has_column(inspector, "ingest_jobs", "current_phase"):
        op.add_column(
            "ingest_jobs",
            sa.Column("current_phase", sa.String, nullable=True),
        )

    if not _has_column(inspector, "ingest_jobs", "phase_start_time"):
        op.add_column(
            "ingest_jobs",
            sa.Column("phase_start_time", sa.DateTime(timezone=True), nullable=True),
        )

    if not _has_column(inspector, "ingest_jobs", "phase_durations"):
        op.add_column(
            "ingest_jobs",
            sa.Column("phase_durations", sa.JSON, nullable=True),
        )

    if not _has_column(inspector, "ingest_jobs", "estimated_completion"):
        op.add_column(
            "ingest_jobs",
            sa.Column("estimated_completion", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade_analysis() -> None:
    """Remove ETA tracking columns."""
    # These are safe to drop as they're only used for display optimization
    op.drop_column("ingest_jobs", "current_phase", if_exists=True)
    op.drop_column("ingest_jobs", "phase_start_time", if_exists=True)
    op.drop_column("ingest_jobs", "phase_durations", if_exists=True)
    op.drop_column("ingest_jobs", "estimated_completion", if_exists=True)


def upgrade_spec() -> None:
    """No-op for Spec DB."""
    pass


def downgrade_spec() -> None:
    """No-op for Spec DB."""
    pass
