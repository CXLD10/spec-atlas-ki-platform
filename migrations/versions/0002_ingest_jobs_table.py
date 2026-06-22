"""Add ingest_jobs table (T-017.3)

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-20

Creates ingest_jobs table in Analysis DB for tracking async ingest job status.
This is ephemeral data (can be cleaned up after job completion) but needs
persistence across restarts.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from spec_atlas.db.analysis import AnalysisBase

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(engine_name: str) -> None:
    globals()[f"upgrade_{engine_name}"]()


def downgrade(engine_name: str) -> None:
    globals()[f"downgrade_{engine_name}"]()


def upgrade_analysis() -> None:
    """Create ingest_jobs table in Analysis DB."""
    bind = op.get_bind()
    # Create only the ingest_jobs table (not entire metadata)
    from spec_atlas.db.analysis import IngestJob

    IngestJob.__table__.create(bind, checkfirst=True)


def downgrade_analysis() -> None:
    """Drop ingest_jobs table."""
    from spec_atlas.db.analysis import IngestJob

    IngestJob.__table__.drop(op.get_bind(), checkfirst=True)


def upgrade_spec() -> None:
    """No-op for Spec DB (ingest jobs belong to Analysis DB only)."""
    pass


def downgrade_spec() -> None:
    """No-op for Spec DB."""
    pass
