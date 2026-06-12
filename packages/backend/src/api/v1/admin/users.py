"""
Admin Users API

GET /  — paginated, filterable user list with optional linked vendor summary.

Mounted at /api/v1/admin/users in main.py.
"""
import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import require_admin
from src.config.database import get_session
from src.models.user import User
from src.models.vendor import Vendor
from src.schemas.admin import AdminUserRead, AdminUserVendorSummary

import structlog

logger = structlog.get_logger()
router = APIRouter(tags=["Admin Users"])


# ---------------------------------------------------------------------------
# GET / — paginated user list with optional vendor join
# ---------------------------------------------------------------------------

@router.get("/", response_model=None)
async def list_users(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
    role: Optional[str] = Query(default=None, description="Filter by user role (user | vendor | admin)"),
    q: Optional[str] = Query(default=None, description="Search email, first_name, or last_name"),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Admin-only: Return a paginated, filterable list of all users.

    Uses a LEFT OUTER JOIN on the vendors table (vendors.user_id = users.id) to
    fetch the linked vendor summary in a single query — no N+1 queries.

    - `role` filters by user role string.
    - `q` performs a case-insensitive ILIKE search on email, first_name, and last_name.
    - Results are ordered by created_at DESC.
    """
    # Base statement: LEFT OUTER JOIN vendors on vendors.user_id = users.id
    stmt = (
        select(User, Vendor)
        .outerjoin(Vendor, Vendor.user_id == User.id)
        .order_by(User.created_at.desc())
    )

    if role is not None:
        stmt = stmt.where(User.role == role)

    if q:
        stmt = stmt.where(
            or_(
                User.email.ilike(f"%{q}%"),
                User.first_name.ilike(f"%{q}%"),
                User.last_name.ilike(f"%{q}%"),
            )
        )

    # Count total matching rows for pagination meta
    # Use a subquery of just the User part to avoid duplicates from the join
    count_stmt = (
        select(func.count(User.id))
        .outerjoin(Vendor, Vendor.user_id == User.id)
    )
    if role is not None:
        count_stmt = count_stmt.where(User.role == role)
    if q:
        count_stmt = count_stmt.where(
            or_(
                User.email.ilike(f"%{q}%"),
                User.first_name.ilike(f"%{q}%"),
                User.last_name.ilike(f"%{q}%"),
            )
        )
    total: int = (await session.execute(count_stmt)).scalar_one()

    # Apply pagination
    stmt = stmt.offset((page - 1) * limit).limit(limit)
    rows = (await session.execute(stmt)).all()

    pages = math.ceil(total / limit) if total > 0 else 1

    # Build response items
    data = []
    for user, vendor in rows:
        vendor_summary: Optional[AdminUserVendorSummary] = None
        if vendor is not None:
            vendor_summary = AdminUserVendorSummary(
                id=vendor.id,
                business_name=vendor.business_name,
                status=vendor.status,
            )

        user_read = AdminUserRead(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            is_active=user.is_active,
            email_verified=user.email_verified,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            vendor=vendor_summary,
            subscription_status=user.subscription_status,
            subscription_expires_at=user.subscription_expires_at,
        )
        data.append(user_read.model_dump())

    logger.info(
        "admin.users.listed",
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
