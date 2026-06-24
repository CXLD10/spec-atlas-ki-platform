"""Add session_id to spec_db tables for multi-user isolation

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-24

Spec DB only:
- specs.session_id (String, NOT NULL) — session identifier for multi-user isolation
- spec_edges.session_id (String, NOT NULL) — session identifier for spec edges
- embeddings.session_id (String, NOT NULL) — session identifier for embeddings

This enables per-user isolation in the Spec DB, matching the Analysis DB schema.
Backfilled with default UUID for all existing rows.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_SESSION_ID = "00000000-0000-0000-0000-000000000000"


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

    tables = ["specs", "spec_edges"]

    for table in tables:
        if not _has_column(inspector, table, "session_id"):
            # Add column as nullable first
            op.add_column(
                table,
                sa.Column("session_id", sa.String, nullable=True),
            )

            # Backfill with default session ID
            op.execute(
                f"UPDATE {table} SET session_id = '{DEFAULT_SESSION_ID}' WHERE session_id IS NULL"
            )

            # Make NOT NULL
            op.alter_column(table, "session_id", nullable=False)

            # Add index
            op.create_index(f"ix_{table}_session_id", table, ["session_id"])


def downgrade_spec() -> None:
    tables = ["specs", "spec_edges"]

    for table in reversed(tables):
        op.drop_index(f"ix_{table}_session_id", table_name=table)
        op.drop_column(table, "session_id")
