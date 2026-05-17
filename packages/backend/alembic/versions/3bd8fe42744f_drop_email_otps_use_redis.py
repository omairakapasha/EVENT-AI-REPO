"""drop_email_otps_use_redis

OTP storage has been migrated from the email_otps PostgreSQL table to Redis
(native TTL, O(1) lookups, automatic eviction). This migration drops the
email_otps table and its index. The downgrade() recreates the table fully
so the migration is reversible.

Revision ID: 3bd8fe42744f
Revises: 9fdc2aedeb71
Create Date: 2026-05-17 17:07:46.854498

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3bd8fe42744f"
down_revision: Union[str, Sequence[str], None] = "9fdc2aedeb71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the email_otps table — OTP state is now stored in Redis."""
    op.drop_index("ix_email_otps_user_id", table_name="email_otps")
    op.drop_table("email_otps")


def downgrade() -> None:
    """Recreate the email_otps table (fully reversible)."""
    op.create_table(
        "email_otps",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_email_otps_user_id", "email_otps", ["user_id"])
