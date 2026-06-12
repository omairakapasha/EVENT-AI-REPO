"""add negotiation loop — quotes, counter_offers, booking state expansion

Revision ID: 20260602_negotiation_loop
Revises: 20260521_add_subscription_fields
Create Date: 2026-06-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260602_negotiation_loop"
down_revision: Union[str, Sequence[str], None] = "20260521_add_subscription_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

quote_status_enum = postgresql.ENUM(
    "draft", "sent", "accepted", "countered", "expired", "withdrawn",
    name="quotestatus",
)
counter_offer_status_enum = postgresql.ENUM(
    "pending", "accepted", "rejected", "superseded",
    name="counterofferstatus",
)


def upgrade() -> None:
    # ── customer_inquiries — recreate (dropped by 572da3239ca3) ───────────────
    op.create_table(
        "customer_inquiries",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("vendor_id", sa.UUID(), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("customer_email", sa.String(length=255), nullable=False),
        sa.Column("customer_phone", sa.String(length=50), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("preferred_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=True),
        sa.Column("expected_guests", sa.Integer(), nullable=True),
        sa.Column("budget_range", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="NEW"),
        sa.Column("vendor_response", sa.Text(), nullable=True),
        sa.Column("vendor_responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quote_id", sa.UUID(), nullable=True),
        sa.Column("quoted_amount", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_inquiries_vendor_id", "customer_inquiries", ["vendor_id"])
    op.create_index("ix_customer_inquiries_customer_email", "customer_inquiries", ["customer_email"])
    op.create_index("ix_customer_inquiries_quote_id", "customer_inquiries", ["quote_id"])

    # ── quotes ────────────────────────────────────────────────────────────────
    op.create_table(
        "quotes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("booking_id", sa.UUID(), nullable=True),
        sa.Column("inquiry_id", sa.UUID(), nullable=True),
        sa.Column("vendor_id", sa.UUID(), nullable=False),
        sa.Column("line_items", sa.JSON(), nullable=True),
        sa.Column("subtotal", sa.Float(), nullable=False, server_default="0"),
        sa.Column("deposit_required", sa.Float(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="PKR"),
        sa.Column("valid_until", sa.DateTime(), nullable=True),
        sa.Column("status", quote_status_enum, nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("round_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inquiry_id"], ["customer_inquiries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quotes_booking_id", "quotes", ["booking_id"])
    op.create_index("ix_quotes_inquiry_id", "quotes", ["inquiry_id"])
    op.create_index("ix_quotes_vendor_id", "quotes", ["vendor_id"])

    # ── counter_offers ────────────────────────────────────────────────────────
    op.create_table(
        "counter_offers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("quote_id", sa.UUID(), nullable=False),
        sa.Column("proposed_by_user_id", sa.UUID(), nullable=False),
        sa.Column("proposed_total", sa.Float(), nullable=False),
        sa.Column("proposed_changes", sa.JSON(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", counter_offer_status_enum, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposed_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_counter_offers_quote_id", "counter_offers", ["quote_id"])
    op.create_index("ix_counter_offers_proposed_by_user_id", "counter_offers", ["proposed_by_user_id"])

    # ── bookings.status — extend bookingstatus enum for negotiation states ─────
    op.execute("ALTER TYPE bookingstatus ADD VALUE IF NOT EXISTS 'awaiting_deposit' BEFORE 'confirmed'")
    op.execute("ALTER TYPE bookingstatus ADD VALUE IF NOT EXISTS 'accepted' BEFORE 'awaiting_deposit'")
    op.execute("ALTER TYPE bookingstatus ADD VALUE IF NOT EXISTS 'negotiating' BEFORE 'accepted'")
    op.execute("ALTER TYPE bookingstatus ADD VALUE IF NOT EXISTS 'quoted' BEFORE 'negotiating'")


def downgrade() -> None:
    # Postgres does not support removing enum values without recreating the type.
    # Intentionally a no-op for the bookingstatus additions.

    op.drop_index("ix_counter_offers_proposed_by_user_id", table_name="counter_offers")
    op.drop_index("ix_counter_offers_quote_id", table_name="counter_offers")
    op.drop_table("counter_offers")

    op.drop_index("ix_quotes_vendor_id", table_name="quotes")
    op.drop_index("ix_quotes_inquiry_id", table_name="quotes")
    op.drop_index("ix_quotes_booking_id", table_name="quotes")
    op.drop_table("quotes")

    counter_offer_status_enum.drop(op.get_bind(), checkfirst=True)
    quote_status_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_customer_inquiries_quote_id", table_name="customer_inquiries")
    op.drop_index("ix_customer_inquiries_customer_email", table_name="customer_inquiries")
    op.drop_index("ix_customer_inquiries_vendor_id", table_name="customer_inquiries")
    op.drop_table("customer_inquiries")
