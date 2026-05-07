"""
VendorApiKeyService — create, list, and revoke vendor API keys.

Keys are generated as cryptographically random tokens, stored as SHA-256
hashes. The raw key is returned exactly once at creation.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import List

import structlog
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.vendor_api_key import VendorApiKey
from src.schemas.vendor_api_key import VendorApiKeyCreate, VendorApiKeyCreated, VendorApiKeyRead

log = structlog.get_logger()

_KEY_PREFIX = "evai_"
_MAX_KEYS_PER_VENDOR = 10


def _generate_raw_key() -> str:
    """Return a URL-safe random key with a recognisable prefix."""
    return _KEY_PREFIX + secrets.token_urlsafe(32)


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


class VendorApiKeyService:
    async def list_keys(
        self, session: AsyncSession, vendor_id: uuid.UUID
    ) -> List[VendorApiKeyRead]:
        rows = (
            await session.execute(
                select(VendorApiKey)
                .where(VendorApiKey.vendor_id == vendor_id)
                .order_by(VendorApiKey.created_at.desc())
            )
        ).scalars().all()
        return [VendorApiKeyRead.model_validate(r) for r in rows]

    async def create_key(
        self,
        session: AsyncSession,
        vendor_id: uuid.UUID,
        data: VendorApiKeyCreate,
    ) -> VendorApiKeyCreated:
        # Enforce per-vendor key limit
        count = len(
            (
                await session.execute(
                    select(VendorApiKey).where(
                        VendorApiKey.vendor_id == vendor_id,
                        VendorApiKey.is_active == True,  # noqa: E712
                    )
                )
            ).scalars().all()
        )
        if count >= _MAX_KEYS_PER_VENDOR:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "CONFLICT_API_KEY_LIMIT",
                    "message": f"Maximum of {_MAX_KEYS_PER_VENDOR} active API keys allowed.",
                },
            )

        raw_key = _generate_raw_key()
        key_hash = _hash_key(raw_key)
        key_prefix = raw_key[:12]  # "evai_" + 7 chars

        db_key = VendorApiKey(
            vendor_id=vendor_id,
            name=data.name,
            key_hash=key_hash,
            key_prefix=key_prefix,
        )
        session.add(db_key)
        await session.commit()
        await session.refresh(db_key)

        log.info("vendor_api_key.created", vendor_id=str(vendor_id), key_id=str(db_key.id))

        return VendorApiKeyCreated(
            id=db_key.id,
            name=db_key.name,
            key_prefix=db_key.key_prefix,
            is_active=db_key.is_active,
            last_used_at=db_key.last_used_at,
            expires_at=db_key.expires_at,
            created_at=db_key.created_at,
            raw_key=raw_key,
        )

    async def revoke_key(
        self,
        session: AsyncSession,
        vendor_id: uuid.UUID,
        key_id: uuid.UUID,
    ) -> None:
        key = await session.get(VendorApiKey, key_id)
        if not key or key.vendor_id != vendor_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND_API_KEY", "message": "API key not found."},
            )
        if not key.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "CONFLICT_API_KEY_REVOKED", "message": "API key is already revoked."},
            )
        key.is_active = False
        key.revoked_at = datetime.now(timezone.utc)
        await session.commit()
        log.info("vendor_api_key.revoked", vendor_id=str(vendor_id), key_id=str(key_id))


vendor_api_key_service = VendorApiKeyService()
