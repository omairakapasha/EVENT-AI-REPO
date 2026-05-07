"""
Pydantic schemas for VendorApiKey endpoints.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VendorApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class VendorApiKeyRead(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class VendorApiKeyCreated(VendorApiKeyRead):
    """Returned only once at creation — includes the raw key."""
    raw_key: str
