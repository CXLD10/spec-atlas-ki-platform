"""Create groq_key_status table for rate limit tracking.

Revision ID: 004_groq_key_status
Revises: 003_add_session_id_spec_db
Create Date: 2026-06-24 11:34:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '004_groq_key_status'
down_revision = '003_add_session_id_spec_db'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('groq_key_status',
        sa.Column('key_index', sa.Integer(), nullable=False),
        sa.Column('last_429_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('consecutive_failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('key_index')
    )


def downgrade() -> None:
    op.drop_table('groq_key_status')
