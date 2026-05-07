"""add_vendor_api_keys_table

Revision ID: 05a9fa9c6dbc
Revises: 20260411_add_vendor_embeddings
Create Date: 2026-05-06 23:36:37.732683

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '05a9fa9c6dbc'
down_revision: Union[str, Sequence[str], None] = '20260411_add_vendor_embeddings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create vendor_api_keys table."""
    op.create_table(
        'vendor_api_keys',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('vendor_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('key_prefix', sa.String(length=16), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_vendor_api_keys_key_hash'),
        'vendor_api_keys', ['key_hash'], unique=True,
    )
    op.create_index(
        op.f('ix_vendor_api_keys_vendor_id'),
        'vendor_api_keys', ['vendor_id'], unique=False,
    )


def downgrade() -> None:
    """Drop vendor_api_keys table."""
    op.drop_index(op.f('ix_vendor_api_keys_vendor_id'), table_name='vendor_api_keys')
    op.drop_index(op.f('ix_vendor_api_keys_key_hash'), table_name='vendor_api_keys')
    op.drop_table('vendor_api_keys')
