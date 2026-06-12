"""
Subscription endpoints.

GET  /subscriptions/me              — current user's subscription status
POST /admin/subscriptions/{user_id}/grant   — admin: grant pro
DELETE /admin/subscriptions/{user_id}/revoke — admin: revoke pro
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, require_admin
from src.config.database import get_session
from src.models.user import User
from src.services.subscription_service import subscription_service

router = APIRouter(tags=["Subscriptions"])
admin_router = APIRouter(tags=["Admin Subscriptions"])


@router.get("/me")
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await subscription_service.get_status(session, current_user.id)


@admin_router.post("/{user_id}/grant")
async def grant_pro(
    user_id: uuid.UUID,
    days: int = Query(default=36500, ge=1, description="Days of pro access"),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await subscription_service.grant_pro(session, user_id, days=days, granted_by=current_user.id)


@admin_router.delete("/{user_id}/revoke")
async def revoke_pro(
    user_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await subscription_service.revoke_pro(session, user_id, revoked_by=current_user.id)
