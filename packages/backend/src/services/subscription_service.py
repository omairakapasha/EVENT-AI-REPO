"""
Subscription service — manages user subscription tiers (free / pro).

Pro users get payment_status=paid automatically on booking creation;
no deposit is required.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import SubscriptionStatus, User
from src.services.event_bus_service import event_bus

logger = structlog.get_logger()

_PRO_DEFAULT_DAYS = 36500  # ~100 years for demo/admin grants


def _err(code: str, message: str) -> dict:
    return {"code": code, "message": message}


class SubscriptionService:

    async def get_status(self, session: AsyncSession, user_id: uuid.UUID) -> dict:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_err("NOT_FOUND_USER", "User not found."),
            )
        is_active = self._is_pro_active(user)
        return {
            "subscription_status": user.subscription_status,
            "is_pro_active": is_active,
            "subscription_expires_at": user.subscription_expires_at,
        }

    async def grant_pro(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        days: int = _PRO_DEFAULT_DAYS,
        granted_by: Optional[uuid.UUID] = None,
    ) -> dict:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_err("NOT_FOUND_USER", "User not found."),
            )
        now = datetime.now(timezone.utc)
        user.subscription_status = SubscriptionStatus.pro
        user.subscription_expires_at = now + timedelta(days=days)
        user.updated_at = now

        await event_bus.emit(
            session,
            "subscription.granted",
            payload={"user_id": str(user_id), "days": days, "granted_by": str(granted_by) if granted_by else None},
            user_id=user_id,
        )
        await session.commit()
        await session.refresh(user)
        logger.info("subscription.granted", user_id=str(user_id), days=days)
        return {
            "subscription_status": user.subscription_status,
            "subscription_expires_at": user.subscription_expires_at,
        }

    async def revoke_pro(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        revoked_by: Optional[uuid.UUID] = None,
    ) -> dict:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_err("NOT_FOUND_USER", "User not found."),
            )
        user.subscription_status = SubscriptionStatus.free
        user.subscription_expires_at = None
        user.updated_at = datetime.now(timezone.utc)

        await event_bus.emit(
            session,
            "subscription.revoked",
            payload={"user_id": str(user_id), "revoked_by": str(revoked_by) if revoked_by else None},
            user_id=user_id,
        )
        await session.commit()
        await session.refresh(user)
        logger.info("subscription.revoked", user_id=str(user_id))
        return {"subscription_status": user.subscription_status}

    def _is_pro_active(self, user: User) -> bool:
        if user.subscription_status != SubscriptionStatus.pro:
            return False
        if user.subscription_expires_at is None:
            return True
        now = datetime.now(timezone.utc)
        expires = user.subscription_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires > now


subscription_service = SubscriptionService()
