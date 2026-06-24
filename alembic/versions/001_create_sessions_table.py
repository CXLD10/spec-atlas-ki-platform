"""Create sessions table for multi-user isolation.

Revision ID: 001_create_sessions
Revises:
Create Date: 2026-06-24 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_create_sessions'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_interaction_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('assigned_groq_key_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('repo_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sessions_expires_at', 'sessions', ['expires_at'])
    op.create_index('ix_sessions_is_deleted', 'sessions', ['is_deleted'])


def downgrade() -> None:
    op.drop_index('ix_sessions_is_deleted', table_name='sessions')
    op.drop_index('ix_sessions_expires_at', table_name='sessions')
    op.drop_table('sessions')
