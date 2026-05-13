"""
Admin Vendors API

GET /          — paginated, filterable vendor list.
PATCH /{vendor_id}/status — update vendor status and emit domain event.

Mounted at /api/v1/admin/vendors in main.py.
"""
import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_event_bus, require_admin
from src.config.database import get_session
from src.models.user import User
from src.models.vendor import Vendor, VendorStatus
from src.schemas.admin import AdminVendorRead, AdminVendorStatusUpdate
from src.services.event_bus_service import EventBusService

import structlog

logger = structlog.get_logger()
router = APIRouter(tags=["Admin Vendors"])


# ---------------------------------------------------------------------------
# Helper: build AdminVendorRead from a Vendor ORM instance
# ---------------------------------------------------------------------------

def _vendor_to_read(vendor: Vendor) -> AdminVendorRead:
    """Map a Vendor ORM row to the AdminVendorRead response schema."""
    return AdminVendorRead(
        id=vendor.id,
        business_name=vendor.business_name,
        status=vendor.status,
        city=vendor.city,
        region=vendor.region,
        rating=vendor.rating,
        total_reviews=vendor.total_reviews,
        created_at=vendor.created_at,
        owner_email=vendor.contact_email,
    )


# ---------------------------------------------------------------------------
# GET / — paginated vendor list
# ---------------------------------------------------------------------------

@router.get("/", response_model=None)
async def list_vendors(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
    status: Optional[VendorStatus] = Query(default=None, description="Filter by vendor status"),
    q: Optional[str] = Query(default=None, description="Search business_name or contact_email"),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Admin-only: Return a paginated, filterable list of all vendors.

    - `status` filters by VendorStatus enum value.
    - `q` performs a case-insensitive ILIKE search on business_name and contact_email.
    - Results are ordered by created_at DESC.
    """
    stmt = select(Vendor).order_by(Vendor.created_at.desc())

    if status is not None:
        stmt = stmt.where(Vendor.status == status)

    if q:
        stmt = stmt.where(
            or_(
                Vendor.business_name.ilike(f"%{q}%"),
                Vendor.contact_email.ilike(f"%{q}%"),
            )
        )

    # Count total matching rows for pagination meta
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await session.execute(count_stmt)).scalar_one()

    # Apply pagination
    stmt = stmt.offset((page - 1) * limit).limit(limit)
    vendors = (await session.execute(stmt)).scalars().all()

    pages = math.ceil(total / limit) if total > 0 else 1

    data = [_vendor_to_read(v).model_dump() for v in vendors]

    logger.info(
        "admin.vendors.listed",
        admin_id=str(current_user.id),
        total=total,
        page=page,
        limit=limit,
    )

    return {
        "success": True,
        "data": data,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        },
    }


# ---------------------------------------------------------------------------
# PATCH /{vendor_id}/status — update vendor status
# ---------------------------------------------------------------------------

# Domain event mapping
_EVENT_TYPE_MAP = {
    VendorStatus.ACTIVE: "vendor.approved",
    VendorStatus.REJECTED: "vendor.rejected",
    VendorStatus.SUSPENDED: "vendor.suspended",
}


@router.patch("/{vendor_id}/status", response_model=None)
async def update_vendor_status(
    vendor_id: uuid.UUID,
    body: AdminVendorStatusUpdate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    event_bus: EventBusService = Depends(get_event_bus),
):
    """
    Admin-only: Update a vendor's status and emit the corresponding domain event.

    - Sets vendor.status to the requested value and commits.
    - Emits vendor.approved / vendor.rejected / vendor.suspended via the event bus.
    - Returns HTTP 404 with NOT_FOUND_VENDOR if the vendor does not exist.
    """
    # Fetch vendor
    result = await session.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor: Optional[Vendor] = result.scalar_one_or_none()

    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND_VENDOR", "message": "Vendor not found."},
        )

    new_status = body.status
    reason = body.reason

    # Persist status change
    vendor.status = new_status
    await session.commit()
    await session.refresh(vendor)

    # Emit domain event (async, persists to outbox)
    event_type = _EVENT_TYPE_MAP.get(new_status)
    if event_type:
        await event_bus.emit(
            session=session,
            event_type=event_type,
            payload={"vendor_id": str(vendor.id), "reason": reason},
            user_id=current_user.id,
        )

    logger.info(
        "admin.vendor.status_updated",
        admin_id=str(current_user.id),
        vendor_id=str(vendor.id),
        new_status=new_status,
    )

    return {
        "success": True,
        "data": _vendor_to_read(vendor).model_dump(),
        "meta": {},
    }
