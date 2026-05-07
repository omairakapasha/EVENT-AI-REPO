"""
VendorApiKey model — hashed API keys for vendor third-party integrations.

Keys are stored as SHA-256 hashes. The raw key is only returned once at
creation time and never stored in plaintext.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, String, Boolean
from sqlmodel import Field, SQLModel


class VendorApiKey(SQLModel, table=True):
    __tablename__ = "vendor_api_keys"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    vendor_id: uuid.UUID = Field(foreign_key="vendors.id", index=True)

    name: str = Field(max_length=100)
    # SHA-256 hex digest of the raw key — never store plaintext
    key_hash: str = Field(max_length=64, index=True, unique=True)
    # First 8 chars of the raw key shown in UI (e.g. "evai_abc")
    key_prefix: str = Field(max_length=16)

    is_active: bool = Field(default=True, sa_column=Column(Boolean, default=True))
    last_used_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    expires_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    revoked_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
