"""add_booking_counter_offered_notification_type

Revision ID: 20260609_counter_offered_notif
Revises: 20260602_negotiation_loop
Create Date: 2026-06-09

Adds booking_counter_offered to the notification_type Postgres ENUM so
the notification service can persist vendor counter-offer alerts.
"""
from typing import Sequence, Union
from alembic import op

revision: str = "20260609_counter_offered_notif"
down_revision: Union[str, Sequence[str], None] = "20260602_negotiation_loop"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'booking_counter_offered'")


def downgrade() -> None:
    # Postgres does not support removing enum values without recreating the type.
    # Intentionally a no-op.
    pass
