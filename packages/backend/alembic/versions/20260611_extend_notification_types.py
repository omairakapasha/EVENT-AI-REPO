"""extend_notification_types

Revision ID: 20260611_extend_notification_types
Revises: 20260610_add_reviews_table
Create Date: 2026-06-11

Adds the NotificationType enum members that exist on the Python side
(src/models/notification.py) but were never added to the Postgres
notificationtype ENUM — including the negotiation-loop notification
types (booking_quoted, booking_accepted, booking_counter_offered,
booking_counter_rejected) required by the quote/counter-offer flow.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260611_extend_notification_types"
down_revision: Union[str, Sequence[str], None] = "20260610_add_reviews_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_VALUES = [
    "booking_counter_offered",
    "booking_quoted",
    "booking_accepted",
    "booking_counter_rejected",
    "vendor_suspended",
    "subscription_granted",
    "subscription_revoked",
    "inquiry_created",
]


def upgrade() -> None:
    for value in NEW_VALUES:
        op.execute(f"ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # Postgres does not support removing enum values without recreating the type.
    # Intentionally a no-op.
    pass
