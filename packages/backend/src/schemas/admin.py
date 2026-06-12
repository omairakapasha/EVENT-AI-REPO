"""
Pydantic/SQLModel schemas for Admin API endpoints.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel

from ..models.vendor import VendorStatus


# ============================================
# Vendor schemas
# ============================================

class AdminVendorRead(SQLModel):
    """Full vendor record returned by admin vendor list / detail endpoints."""

    id: uuid.UUID
    business_name: str
    status: VendorStatus
    city: Optional[str] = None
    region: Optional[str] = None
    rating: float
    total_reviews: int
    created_at: datetime
    owner_email: str  # maps to vendor.contact_email

    model_config = {"from_attributes": True}


class AdminVendorStatusUpdate(SQLModel):
    """Request body for PATCH /{vendor_id}/status."""

    status: VendorStatus
    reason: Optional[str] = None


# ============================================
# User schemas
# ============================================

class AdminUserVendorSummary(SQLModel):
    """Minimal vendor info embedded inside AdminUserRead."""

    id: uuid.UUID
    business_name: str
    status: VendorStatus

    model_config = {"from_attributes": True}


class AdminUserRead(SQLModel):
    """Full user record returned by admin user list endpoint."""

    id: uuid.UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    is_active: bool
    email_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    vendor: Optional[AdminUserVendorSummary] = None
    subscription_status: str = "free"
    subscription_expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ============================================
# Stats schema
# ============================================

class AdminStatsResponse(SQLModel):
    """Aggregated platform statistics returned by GET /admin/stats."""

    totalUsers: int
    activeVendors: int
    pendingVendors: int
    totalBookings: int
    confirmedBookings: int
    pendingBookings: int
    totalRevenue: float
