"""Drop server default 'Pakistan' on events.country (global market)

The product is no longer Pakistan-specific. `country` stays NOT NULL but is now
required input — no hardcoded default — so events carry the vendor/user's actual
country.

Revision ID: 20260618_event_country_no_default
Revises: 20260611_extend_notification_types
Create Date: 2026-06-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260618_event_country_no_default"
down_revision: Union[str, Sequence[str], None] = "20260611_extend_notification_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove the hardcoded 'Pakistan' default; column remains NOT NULL.
    op.alter_column(
        "events",
        "country",
        existing_type=sa.String(length=100),
        existing_nullable=False,
        server_default=None,
    )


def downgrade() -> None:
    op.alter_column(
        "events",
        "country",
        existing_type=sa.String(length=100),
        existing_nullable=False,
        server_default=sa.text("'Pakistan'"),
    )
