"""add subscription fields to users

Revision ID: 20260521_add_subscription_fields
Revises: 3bd8fe42744f
Create Date: 2026-05-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20260521_add_subscription_fields'
down_revision: Union[str, Sequence[str], None] = '3bd8fe42744f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'subscription_status',
            sa.String(length=20),
            nullable=False,
            server_default='free',
        ),
    )
    op.add_column(
        'users',
        sa.Column(
            'subscription_expires_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'subscription_expires_at')
    op.drop_column('users', 'subscription_status')
