"""add_terms_accepted_at

Revision ID: 20260609_terms_accepted_at
Revises: 20260609_counter_offered_notif
Create Date: 2026-06-09

Adds terms_accepted_at (nullable DateTime) to the users table so the platform
can track when each user accepted the Terms & Conditions.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260609_terms_accepted_at"
down_revision: Union[str, Sequence[str], None] = "20260609_counter_offered_notif"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "terms_accepted_at")
