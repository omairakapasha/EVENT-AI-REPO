"""
OTPService — generates, stores, and verifies 6-digit email OTPs.

Security properties:
- OTP is a cryptographically random 6-digit code
- Stored as SHA-256 hash — plaintext never persisted
- Expires in 10 minutes
- Single-use: marked used_at on first successful verification
- Old unused OTPs for the same user are invalidated on new issue
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import structlog

from ..models.email_otp import EmailOTP
from ..services.email_service import email_service

logger = structlog.get_logger()

OTP_EXPIRY_MINUTES = 10
OTP_LENGTH = 6


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OTPService:

    async def issue_otp(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        user_email: str,
        user_name: str = "",
    ) -> str:
        """
        Generate a new OTP, invalidate any existing unused OTPs for this user,
        persist the hash, and send the code via email.
        Returns the plaintext code (for dev logging only — never expose in API).
        """
        # Invalidate all previous unused OTPs for this user
        await session.execute(
            update(EmailOTP)
            .where(
                EmailOTP.user_id == user_id,
                EmailOTP.used_at.is_(None),
            )
            .values(used_at=_utcnow())
        )

        # Generate a zero-padded 6-digit code
        code = str(secrets.randbelow(10 ** OTP_LENGTH)).zfill(OTP_LENGTH)
        expires_at = _utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)

        otp = EmailOTP(
            user_id=user_id,
            code_hash=_hash_code(code),
            expires_at=expires_at,
        )
        session.add(otp)
        await session.commit()

        # Send email via Brevo SMTP
        subject = "Your Event-AI verification code"
        display_name = user_name or user_email
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
            <div style="text-align: center; margin-bottom: 32px;">
                <h1 style="color: #2563eb; font-size: 24px; margin: 0;">Event-AI</h1>
                <p style="color: #6b7280; margin-top: 4px;">Pakistan's Event Planning Marketplace</p>
            </div>
            <h2 style="color: #111827; font-size: 20px;">Verify your email address</h2>
            <p style="color: #374151;">Hi {display_name},</p>
            <p style="color: #374151;">Use the code below to verify your email address. It expires in <strong>{OTP_EXPIRY_MINUTES} minutes</strong>.</p>
            <div style="background: #f3f4f6; border-radius: 12px; padding: 24px; text-align: center; margin: 24px 0;">
                <span style="font-size: 40px; font-weight: 700; letter-spacing: 12px; color: #2563eb; font-family: monospace;">{code}</span>
            </div>
            <p style="color: #6b7280; font-size: 14px;">If you didn't create an account, you can safely ignore this email.</p>
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
            <p style="color: #9ca3af; font-size: 12px; text-align: center;">Event-AI &mdash; Pakistan's Event Planning Marketplace</p>
        </div>
        """
        text_body = f"Your Event-AI verification code is: {code}\n\nIt expires in {OTP_EXPIRY_MINUTES} minutes."

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
        session: AsyncSession,
        user_id: uuid.UUID,
        code: str,
    ) -> bool:
        """
        Verify a submitted OTP code.
        Raises HTTPException on failure (wrong code, expired, already used).
        Returns True on success and marks the OTP as used.
        """
        code_hash = _hash_code(code.strip())
        now = _utcnow()

        result = await session.execute(
            select(EmailOTP).where(
                EmailOTP.user_id == user_id,
                EmailOTP.code_hash == code_hash,
                EmailOTP.used_at.is_(None),
            )
        )
        otp = result.scalar_one_or_none()

        if otp is None:
            logger.warning("otp.invalid", user_id=str(user_id))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "OTP_INVALID", "message": "Invalid or already used verification code."},
            )

        if otp.expires_at.replace(tzinfo=timezone.utc) < now:
            logger.warning("otp.expired", user_id=str(user_id))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "OTP_EXPIRED", "message": "Verification code has expired. Please request a new one."},
            )

        # Mark as used
        otp.used_at = now
        await session.commit()

        logger.info("otp.verified", user_id=str(user_id))
        return True


otp_service = OTPService()
