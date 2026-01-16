"""Add api_keys table

Revision ID: a1b2c3d4e5f6
Revises: d8ffa3747471
Create Date: 2026-01-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd8ffa3747471'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, comment='Human-readable name for the API key'),
        sa.Column('key_hash', sa.String(length=64), nullable=False, comment='SHA-256 hash of the API key'),
        sa.Column('key_prefix', sa.String(length=12), nullable=False, comment='First 8 characters of key for identification'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True, comment='Whether the key is currently active'),
        sa.Column('description', sa.Text(), nullable=True, comment="Optional description of the key's purpose"),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='When the key expires (null = never)'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True, comment='When the key was last used'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='When the key was created'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='When the key was last updated'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_table('api_keys')
