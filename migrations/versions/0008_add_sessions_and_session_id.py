"""Add sessions table and session_id to all tables for multi-user isolation

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-24

Analysis DB:
- Create sessions table (multi-user session management, 2-hour auto-expiry)
- Add session_id to: repos, files, groups, embeddings, nodes, edges, source_units, ingest_jobs

Spec DB:
- session_id already added in migration 0007

All analysis tables backfilled with default session UUID for existing data.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_SESSION_ID = "00000000-0000-0000-0000-000000000000"


def upgrade(engine_name: str) -> None:
    globals()[f"upgrade_{engine_name}"]()


def downgrade(engine_name: str) -> None:
    globals()[f"downgrade_{engine_name}"]()


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspector.get_columns(table))


def _has_table(inspector: sa.Inspector, table: str) -> bool:
    return table in inspector.get_table_names()


def upgrade_analysis() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Step 1: Create sessions table if it doesn't exist
    if not _has_table(inspector, "sessions"):
        op.create_table(
            "sessions",
            sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "last_interaction_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "assigned_groq_key_index",
                sa.Integer,
                nullable=False,
                server_default="0",
            ),
            sa.Column("repo_count", sa.Integer, nullable=False, server_default="0"),
            sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        )
        op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
        op.create_index("ix_sessions_is_deleted", "sessions", ["is_deleted"])

        # Insert default session so backfill works
        op.execute(
            f"INSERT INTO sessions (id, created_at, last_interaction_at, expires_at, assigned_groq_key_index, repo_count, is_deleted) "
            f"VALUES ('{DEFAULT_SESSION_ID}'::uuid, now(), now(), now() + interval '7 days', 0, 0, false) "
            f"ON CONFLICT DO NOTHING"
        )

    # Step 2: Add session_id to all analysis tables
    tables_to_update = [
        "repos",
        "files",
        "groups",
        "embeddings",
        "nodes",
        "edges",
        "source_units",
        "ingest_jobs",
    ]

    for table in tables_to_update:
        # Skip if table doesn't exist or column already exists
        if not _has_table(inspector, table):
            continue
        if _has_column(inspector, table, "session_id"):
            continue

        # Add column as nullable first
        op.add_column(
            table,
            sa.Column("session_id", sa.UUID(as_uuid=True), nullable=True),
        )

        # Backfill with default session ID (for existing rows)
        op.execute(
            f"UPDATE {table} SET session_id = '{DEFAULT_SESSION_ID}'::uuid WHERE session_id IS NULL"
        )

        # Make NOT NULL
        op.alter_column(table, "session_id", nullable=False)

        # Add index
        op.create_index(f"ix_{table}_session_id", table, ["session_id"])

        # For repos, files, groups, nodes, edges, source_units add FK to sessions (ingest_jobs doesn't have FK)
        if table in ["repos", "files", "groups", "nodes", "edges", "source_units"]:
            op.create_foreign_key(
                f"fk_{table}_session_id",
                table,
                "sessions",
                ["session_id"],
                ["id"],
                ondelete="CASCADE",
            )


def downgrade_analysis() -> None:
    tables_to_update = [
        "repos",
        "files",
        "groups",
        "embeddings",
        "nodes",
        "edges",
        "source_units",
        "ingest_jobs",
    ]

    for table in reversed(tables_to_update):
        op.drop_index(f"ix_{table}_session_id", table_name=table)
        if table in ["repos", "files", "groups", "nodes", "edges", "source_units"]:
            op.drop_constraint(f"fk_{table}_session_id", table, type_="foreignkey")
        op.drop_column(table, "session_id")

    op.drop_index("ix_sessions_is_deleted", table_name="sessions")
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_table("sessions")


def upgrade_spec() -> None:
    pass


def downgrade_spec() -> None:
    pass
