"""Add session_id to spec_db tables.

Revision ID: 003_add_session_id_spec_db
Revises: 002_add_session_id
Create Date: 2026-06-24 11:33:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003_add_session_id_spec_db'
down_revision = '002_add_session_id'
branch_labels = None
depends_on = None

DEFAULT_SESSION_ID = '00000000-0000-0000-0000-000000000000'

def upgrade() -> None:
    # Create sessions table in spec_db context
    # (assumes shared sessions table accessible from both DBs)

    # Add session_id to spec_db tables
    spec_tables = ['specs', 'embeddings']

    for table in spec_tables:
        op.add_column(table,
            sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Backfill
    for table in spec_tables:
        op.execute(f"UPDATE {table} SET session_id = '{DEFAULT_SESSION_ID}' WHERE session_id IS NULL")

    # Make NOT NULL
    for table in spec_tables:
        op.alter_column(table, 'session_id', nullable=False)

    # Add foreign keys and indexes
    for table in spec_tables:
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
    spec_tables = ['specs', 'embeddings']

    for table in reversed(spec_tables):
        op.drop_index(f'ix_{table}_session_id', table_name=table)
        op.drop_constraint(f'fk_{table}_session_id', table, type_='foreignkey')
        op.drop_column(table, 'session_id')
