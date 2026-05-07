"""
Vendor self-service endpoints.
All routes require JWT authentication.
"""
import uuid
from datetime import date as date_type
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select as sa_select, func

from ..deps import get_current_user
from ...config.database import get_session
from ...models.user import User
from ...models.vendor import Vendor, VendorStatus
from ...models.service import Service
from ...schemas.vendor import VendorCreate, VendorUpdate, VendorRead
from ...schemas.service import ServiceRead
from ...schemas.vendor_dashboard import DashboardStats
from ...schemas.vendor_availability import AvailabilityUpsert, BulkAvailabilityUpsert, AvailabilityRead
from ...services.vendor_service import vendor_service
from ...services.vendor_dashboard_service import vendor_dashboard_service
from ...services.vendor_availability_service import vendor_availability_service
from ...services.vendor_api_key_service import vendor_api_key_service
from ...schemas.vendor_api_key import VendorApiKeyCreate, VendorApiKeyRead, VendorApiKeyCreated
from src.models.booking import Booking, BookingRead, BookingStatus
import structlog

log = structlog.get_logger()
router = APIRouter(tags=["Vendors"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _err(code: str, message: str) -> dict:
    return {"code": code, "message": message}


async def _get_vendor_or_404(session: AsyncSession, user_id: uuid.UUID) -> Vendor:
    """Return the vendor profile for the given user, or raise 404."""
    vendor = (
        await session.execute(sa_select(Vendor).where(Vendor.user_id == user_id))
    ).scalar_one_or_none()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_err("NOT_FOUND_VENDOR_PROFILE", "Vendor profile not found."),
        )
    return vendor


# ── Registration & Profile ────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=VendorRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_vendor(
    vendor_in: VendorCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Register the current authenticated user as a marketplace vendor."""
    try:
        vendor = await vendor_service.create_vendor(session, current_user, vendor_in)
        return vendor
    except ValueError as e:
        msg = str(e)
        if msg == "CONFLICT_VENDOR_EXISTS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_err("CONFLICT_VENDOR_EXISTS", "A vendor profile already exists for this account."),
            )
        if msg == "CONFLICT_DUPLICATE_VENDOR":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_err("CONFLICT_DUPLICATE_VENDOR", "A vendor with this business name already exists in this location."),
            )
        if "Invalid category IDs" in msg:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_err("VALIDATION_INVALID_CATEGORY", "One or more category IDs are invalid."),
            )
        log.error("vendor.register.failed", error=msg, user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_err("INTERNAL_ERROR", "An unexpected error occurred."),
        )


@router.get("/profile/me", response_model=VendorRead)
async def get_my_vendor_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get the current authenticated user's vendor profile."""
    vendor = await vendor_service.get_by_user_id(session, current_user.id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_err("NOT_FOUND_VENDOR_PROFILE", "Vendor profile not found."),
        )
    return vendor


@router.put("/profile/me", response_model=VendorRead)
async def update_vendor_profile(
    vendor_in: VendorUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update own vendor profile."""
    vendor = await _get_vendor_or_404(session, current_user.id)
    try:
        return await vendor_service.update_vendor(session, vendor, vendor_in)
    except ValueError as e:
        msg = str(e)
        if "Invalid category IDs" in msg:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_err("VALIDATION_INVALID_CATEGORY", "One or more category IDs are invalid."),
            )
        log.error("vendor.update.failed", error=msg, user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_err("INTERNAL_ERROR", "An unexpected error occurred."),
        )


@router.delete("/profile/me")
async def delete_my_vendor_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Soft-delete (suspend) the current vendor's profile."""
    vendor = await _get_vendor_or_404(session, current_user.id)
    vendor.status = VendorStatus.SUSPENDED
    await session.commit()
    log.info("vendor.deactivated", vendor_id=str(vendor.id), user_id=str(current_user.id))
    return {"success": True, "data": {"message": "Vendor profile deactivated."}, "meta": {}}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/me/dashboard")
async def get_vendor_dashboard(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return aggregated dashboard stats for the authenticated vendor."""
    vendor = await _get_vendor_or_404(session, current_user.id)
    stats = await vendor_dashboard_service.get_dashboard_stats(session, vendor.id)
    return {"success": True, "data": stats.model_dump(), "meta": {}}


# ── Services (vendor-scoped, paginated) ───────────────────────────────────────

@router.get("/me/services")
async def list_vendor_services(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return a paginated list of services for the authenticated vendor."""
    vendor = await _get_vendor_or_404(session, current_user.id)

    base = sa_select(Service).where(
        Service.vendor_id == vendor.id,
        Service.is_active == True,  # noqa: E712
    )
    count_q = sa_select(func.count()).select_from(Service).where(
        Service.vendor_id == vendor.id,
        Service.is_active == True,  # noqa: E712
    )

    if search:
        like = f"%{search}%"
        base = base.where(Service.name.ilike(like))
        count_q = count_q.where(Service.name.ilike(like))

    # Category filter via join (category stored on vendor_category_link, not service directly)
    # Services don't have a direct category FK — filter is a no-op if category is provided
    # but the service model has no category field; skip silently for now.

    total: int = (await session.execute(count_q)).scalar() or 0
    offset = (page - 1) * limit
    rows = (
        await session.execute(
            base.order_by(Service.created_at.desc()).offset(offset).limit(limit)
        )
    ).scalars().all()

    pages = -(-total // limit) if total else 0
    return {
        "success": True,
        "data": [ServiceRead.model_validate(s) for s in rows],
        "meta": {"total": total, "page": page, "limit": limit, "pages": pages},
    }


# ── Availability ──────────────────────────────────────────────────────────────

@router.get("/me/availability")
async def get_vendor_availability(
    start_date: date_type = Query(...),
    end_date: date_type = Query(...),
    service_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return availability records for the authenticated vendor within a date range."""
    vendor = await _get_vendor_or_404(session, current_user.id)
    records = await vendor_availability_service.list_availability(
        session, vendor.id, start_date, end_date, service_id
    )
    return {
        "success": True,
        "data": [AvailabilityRead.model_validate(r) for r in records],
        "meta": {},
    }


@router.post("/me/availability")
async def upsert_vendor_availability(
    body: AvailabilityUpsert,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create or update a single availability slot for the authenticated vendor."""
    vendor = await _get_vendor_or_404(session, current_user.id)
    record = await vendor_availability_service.upsert_availability(session, vendor.id, body)
    return {"success": True, "data": AvailabilityRead.model_validate(record), "meta": {}}


@router.post("/me/availability/bulk")
async def bulk_upsert_vendor_availability(
    body: BulkAvailabilityUpsert,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Bulk-upsert availability slots for the authenticated vendor in one transaction."""
    vendor = await _get_vendor_or_404(session, current_user.id)
    records = await vendor_availability_service.bulk_upsert_availability(
        session, vendor.id, body.entries
    )
    return {
        "success": True,
        "data": [AvailabilityRead.model_validate(r) for r in records],
        "meta": {},
    }


# ── Bookings ──────────────────────────────────────────────────────────────────

@router.get("/me/bookings")
async def list_vendor_bookings(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    booking_status: Optional[BookingStatus] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List bookings for the authenticated vendor, sorted by event_date descending."""
    vendor = await _get_vendor_or_404(session, current_user.id)

    base = sa_select(Booking).where(Booking.vendor_id == vendor.id)
    count_q = sa_select(func.count()).select_from(Booking).where(Booking.vendor_id == vendor.id)

    if booking_status:
        base = base.where(Booking.status == booking_status)
        count_q = count_q.where(Booking.status == booking_status)

    total: int = (await session.execute(count_q)).scalar() or 0
    offset = (page - 1) * limit
    rows = (
        await session.execute(
            base.order_by(Booking.event_date.desc()).offset(offset).limit(limit)
        )
    ).scalars().all()

    return {
        "success": True,
        "data": [BookingRead.model_validate(b) for b in rows],
        "meta": {"total": total, "page": page, "limit": limit, "pages": -(-total // limit) if total else 0},
    }


class VendorBookingStatusBody(BaseModel):
    status: BookingStatus
    reason: Optional[str] = None


@router.patch("/me/bookings/{booking_id}/status")
async def vendor_update_booking_status(
    booking_id: uuid.UUID,
    body: VendorBookingStatusBody,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Vendor confirms or rejects a booking."""
    from src.services.booking_service import booking_service

    vendor = await _get_vendor_or_404(session, current_user.id)
    booking = await session.get(Booking, booking_id)
    if not booking or booking.vendor_id != vendor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_err("AUTH_FORBIDDEN", "Not your booking."),
        )
    updated = await booking_service.update_status(
        session, booking_id, body.status, current_user.id, reason=body.reason
    )
    return {"success": True, "data": BookingRead.model_validate(updated), "meta": {}}


# ── API Keys ──────────────────────────────────────────────────────────────────

@router.get("/me/api-keys", response_model=list[VendorApiKeyRead])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all API keys for the authenticated vendor."""
    vendor = await _get_vendor_or_404(session, current_user.id)
    return await vendor_api_key_service.list_keys(session, vendor.id)


@router.post(
    "/me/api-keys",
    response_model=VendorApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    body: VendorApiKeyCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new API key for the authenticated vendor.

    The `raw_key` field in the response is shown **only once** — store it
    securely. It cannot be retrieved again.
    """
    vendor = await _get_vendor_or_404(session, current_user.id)
    return await vendor_api_key_service.create_key(session, vendor.id, body)


@router.delete("/me/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Revoke (soft-delete) an API key. This action is irreversible."""
    vendor = await _get_vendor_or_404(session, current_user.id)
    await vendor_api_key_service.revoke_key(session, vendor.id, key_id)
