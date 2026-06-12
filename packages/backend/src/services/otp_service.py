"""
OTPService — generates, stores, and verifies 6-digit email OTPs.

Security properties:
- OTP is a cryptographically random 6-digit code
- Stored as SHA-256 hash — plaintext never persisted
- Expires in 10 minutes (TTL enforced natively by Redis)
- Single-use: Redis key deleted on first successful verification
- Old unused OTPs for the same user are atomically overwritten on new issue
"""
import hashlib
import secrets
import uuid

import redis.asyncio as aioredis
from fastapi import HTTPException, status
import structlog

from ..services.email_service import email_service

logger = structlog.get_logger()

OTP_EXPIRY_SECONDS = 600  # 10 minutes
OTP_LENGTH = 6


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


class OTPService:

    async def issue_otp(
        self,
        redis: aioredis.Redis,
        user_id: uuid.UUID,
        user_email: str,
        user_name: str = "",
    ) -> str:
        """
        Generate a new OTP, atomically overwrite any existing OTP for this user
        in Redis with a TTL of 600 seconds, and send the code via email.
        Returns the plaintext code (for dev logging only — never expose in API).
        """
        # Generate a zero-padded 6-digit code
        code = str(secrets.randbelow(10 ** OTP_LENGTH)).zfill(OTP_LENGTH)
        code_hash = _hash_code(code)

        # Atomically store hash in Redis, overwriting any previous key, TTL=600s
        await redis.set(f"otp:{user_id}", code_hash, ex=OTP_EXPIRY_SECONDS)

        subject = "Your Event-AI verification code"
        display_name = user_name or user_email
        otp_expiry_minutes = OTP_EXPIRY_SECONDS // 60
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
            <div style="text-align: center; margin-bottom: 32px;">
                <h1 style="color: #2563eb; font-size: 24px; margin: 0;">Event-AI</h1>
                <p style="color: #6b7280; margin-top: 4px;">Pakistan's Event Planning Marketplace</p>
            </div>
            <h2 style="color: #111827; font-size: 20px;">Verify your email address</h2>
            <p style="color: #374151;">Hi {display_name},</p>
            <p style="color: #374151;">Use the code below to verify your email address. It expires in <strong>{otp_expiry_minutes} minutes</strong>.</p>
            <div style="background: #f3f4f6; border-radius: 12px; padding: 24px; text-align: center; margin: 24px 0;">
                <span style="font-size: 40px; font-weight: 700; letter-spacing: 12px; color: #2563eb; font-family: monospace;">{code}</span>
            </div>
            <p style="color: #6b7280; font-size: 14px;">If you didn't create an account, you can safely ignore this email.</p>
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
            <p style="color: #9ca3af; font-size: 12px; text-align: center;">Event-AI &mdash; Pakistan's Event Planning Marketplace</p>
        </div>
        """
        text_body = f"Your Event-AI verification code is: {code}\n\nIt expires in {otp_expiry_minutes} minutes."

        await email_service.send_email(
            to=user_email,
            subject=subject,
            body_html=html_body,
            body_text=text_body,
        )

        logger.info("otp.issued", user_id=str(user_id), email=user_email)
        return code  # only used for dev-mode logging in email_service

    async def verify_otp(
        self,
        redis: aioredis.Redis,
        user_id: uuid.UUID,
        code: str,
    ) -> bool:
        """
        Verify a submitted OTP code against the Redis-stored hash.
        Raises HTTPException on failure (wrong code, expired/absent key).
        Returns True on success and deletes the Redis key (single-use guarantee).
        """
        code_hash = _hash_code(code.strip())

        stored = await redis.get(f"otp:{user_id}")

        if stored is None:
            # Key absent = TTL elapsed (expired) or never issued.
            # Dominant UX case is expiry, so raise OTP_EXPIRED.
            logger.warning("otp.expired", user_id=str(user_id))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "OTP_EXPIRED", "message": "Verification code has expired. Please request a new one."},
            )

        if stored != code_hash:
            logger.warning("otp.invalid", user_id=str(user_id))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "OTP_INVALID", "message": "Invalid or already used verification code."},
            )

        # Correct code — delete key to enforce single-use guarantee
        await redis.delete(f"otp:{user_id}")

        logger.info("otp.verified", user_id=str(user_id))
        return True


otp_service = OTPService()
