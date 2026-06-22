"""initial schema — Analysis DB (L1+L4+embeddings) and Spec DB (L2+L3)

Revision ID: 0001
Revises:
Create Date: 2026-06-19

Creates both databases' tables from the SQLAlchemy model metadata so the schema
cannot drift from the models, and enables the pgvector extension on the Analysis
DB before the ``embeddings.vector(384)`` column is created.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from spec_atlas.db.analysis import AnalysisBase
from spec_atlas.db.spec import SpecBase

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(engine_name: str) -> None:
    globals()[f"upgrade_{engine_name}"]()


def downgrade(engine_name: str) -> None:
    globals()[f"downgrade_{engine_name}"]()


def upgrade_analysis() -> None:
    bind = op.get_bind()
    # pgvector must exist before the embeddings.vector(384) column is created.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    AnalysisBase.metadata.create_all(bind=bind)


def downgrade_analysis() -> None:
    AnalysisBase.metadata.drop_all(bind=op.get_bind())


def upgrade_spec() -> None:
    SpecBase.metadata.create_all(bind=op.get_bind())


def downgrade_spec() -> None:
    SpecBase.metadata.drop_all(bind=op.get_bind())
