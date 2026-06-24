"""Add session_id to all analysis_db tables for multi-user isolation.

Revision ID: 002_add_session_id
Revises: 001_create_sessions
Create Date: 2026-06-24 11:32:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

revision = '002_add_session_id'
down_revision = '001_create_sessions'
branch_labels = None
depends_on = None

# Default session ID for existing data
DEFAULT_SESSION_ID = '00000000-0000-0000-0000-000000000000'

def upgrade() -> None:
    # Add session_id to all tables (nullable initially for backfill)
    tables = ['repos', 'files', 'nodes', 'edges', 'groups', 'ingest_jobs']

    for table in tables:
        # Check if column exists
        op.add_column(table,
            sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Backfill existing data with default session
    for table in tables:
        op.execute(f"UPDATE {table} SET session_id = '{DEFAULT_SESSION_ID}' WHERE session_id IS NULL")

    # Make NOT NULL
    for table in tables:
        op.alter_column(table, 'session_id', nullable=False)

    # Add foreign keys and indexes
    for table in tables:
        op.create_foreign_key(
            f'fk_{table}_session_id',
            table,
            'sessions',
            ['session_id'],
            ['id'],
            ondelete='CASCADE'
        )
        op.create_index(f'ix_{table}_session_id', table, ['session_id'])


def downgrade() -> None:
    tables = ['repos', 'files', 'nodes', 'edges', 'groups', 'ingest_jobs']

    for table in reversed(tables):
        op.drop_index(f'ix_{table}_session_id', table_name=table)
        op.drop_constraint(f'fk_{table}_session_id', table, type_='foreignkey')
        op.drop_column(table, 'session_id')
