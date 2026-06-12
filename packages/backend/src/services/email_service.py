"""
Email Service — Brevo transactional API (primary) with SMTP fallback.
Dev mode: logs to console when neither is configured.
"""
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import structlog

from src.config.database import get_settings

logger = structlog.get_logger()

_BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"


class EmailService:
    """Fire-and-forget email dispatch — never blocks the caller."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._brevo_configured = bool(self._settings.brevo_api_key)
        self._smtp_configured = bool(
            self._settings.smtp_host and self._settings.smtp_user
        )

    async def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> bool:
        """
        Send email (fire-and-forget).
        Priority: Brevo API → SMTP → dev console log.
        Returns True if dispatched, False if skipped.
        """
        if self._brevo_configured:
            asyncio.create_task(
                self._send_brevo(
                    to=to,
                    subject=subject,
                    body_html=body_html,
                    body_text=body_text,
                    from_email=from_email,
                    reply_to=reply_to,
                )
            )
            return True

        if self._smtp_configured:
            asyncio.create_task(
                self._send_smtp(
                    to=to,
                    subject=subject,
                    body_html=body_html,
                    body_text=body_text,
                    from_email=from_email,
                    reply_to=reply_to,
                )
            )
            return True

        logger.info(
            "email.dev_mode",
            to=to,
            subject=subject,
            body_preview=(body_text or body_html)[:200],
        )
        return True

    async def _send_brevo(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        max_retries: int = 3,
    ) -> bool:
        s = self._settings
        sender_email = from_email or s.email_from
        payload: dict[str, Any] = {
            "sender": {"name": s.email_from_name, "email": sender_email},
            "to": [{"email": to}],
            "subject": subject,
            "htmlContent": body_html,
        }
        if body_text:
            payload["textContent"] = body_text
        if reply_to:
            payload["replyTo"] = {"email": reply_to}

        headers = {
            "api-key": s.brevo_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(_BREVO_SEND_URL, json=payload, headers=headers)
                    resp.raise_for_status()
                logger.info("email.sent", provider="brevo", to=to, subject=subject, attempt=attempt)
                return True
            except Exception as exc:
                logger.warning(
                    "email.send_failed",
                    provider="brevo",
                    to=to,
                    subject=subject,
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)

        logger.error("email.permanent_failure", provider="brevo", to=to, subject=subject, attempts=max_retries)
        return False

    async def _send_smtp(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        max_retries: int = 3,
    ) -> bool:
        s = self._settings
        sender = from_email or s.email_from

        for attempt in range(1, max_retries + 1):
            try:
                msg = MIMEMultipart("alternative")
                msg["From"] = sender
                msg["To"] = to
                msg["Subject"] = subject
                if reply_to:
                    msg["Reply-To"] = reply_to
                msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
                if body_text:
                    msg.attach(MIMEText(body_text, "plain"))
                msg.attach(MIMEText(body_html, "html"))

                with smtplib.SMTP(s.smtp_host, s.smtp_port) as server:
                    if s.smtp_secure:
                        server.starttls()
                    if s.smtp_user and s.smtp_password:
                        server.login(s.smtp_user, s.smtp_password)
                    server.sendmail(sender, to, msg.as_string())

                logger.info("email.sent", provider="smtp", to=to, subject=subject, attempt=attempt)
                return True
            except Exception as exc:
                logger.warning(
                    "email.send_failed",
                    provider="smtp",
                    to=to,
                    subject=subject,
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)

        logger.error("email.permanent_failure", provider="smtp", to=to, subject=subject, attempts=max_retries)
        return False

    def render_booking_email(
        self,
        event_type: str,
        vendor_name: str,
        event_date: str,
        event_name: str,
        **extra: Any,
    ) -> tuple[str, str]:
        """Return (subject, html_body) for a booking lifecycle event."""
        templates = {
            "booking.created": (
                "Booking Request Received",
                f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #2563eb;">Booking Request Received</h2>
                    <p>Your booking request has been submitted successfully.</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Vendor:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{vendor_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Event:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Date:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_date}</td></tr>
                    </table>
                    <p style="color: #666;">You will receive a confirmation once the vendor accepts your request.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">Event-AI — Pakistan's Event Planning Marketplace</p>
                </div>
                """,
            ),
            "booking.confirmed": (
                "Booking Confirmed ✓",
                f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #16a34a;">Booking Confirmed ✓</h2>
                    <p>Great news! Your booking has been confirmed.</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Vendor:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{vendor_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Event:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Date:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_date}</td></tr>
                    </table>
                    <p style="color: #666;">Contact the vendor for any additional details.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">Event-AI — Pakistan's Event Planning Marketplace</p>
                </div>
                """,
            ),
            "booking.cancelled": (
                "Booking Cancelled",
                f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #dc2626;">Booking Cancelled</h2>
                    <p>Your booking has been cancelled.</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Vendor:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{vendor_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Event:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Date:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_date}</td></tr>
                    </table>
                    <p style="color: #666;">If you have questions, please contact the vendor.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">Event-AI — Pakistan's Event Planning Marketplace</p>
                </div>
                """,
            ),
            "booking.rejected": (
                "Booking Request Declined",
                f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #dc2626;">Booking Request Declined</h2>
                    <p>Unfortunately, your booking request was declined by the vendor.</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Vendor:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{vendor_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Event:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Date:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_date}</td></tr>
                    </table>
                    <p style="color: #666;">You can search for alternative vendors on our platform.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">Event-AI — Pakistan's Event Planning Marketplace</p>
                </div>
                """,
            ),
            "booking.completed": (
                "Your Event is Complete — Leave a Review!",
                f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #2563eb;">Your Event is Complete! 🎉</h2>
                    <p>We hope you had a wonderful event!</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Vendor:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{vendor_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Event:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Date:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_date}</td></tr>
                    </table>
                    <p style="color: #666;">Help others by leaving a review for your vendor!</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">Event-AI — Pakistan's Event Planning Marketplace</p>
                </div>
                """,
            ),
            "new_booking_request": (
                "New Booking Request",
                f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #2563eb;">New Booking Request</h2>
                    <p>You have received a new booking request.</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Event:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Date:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_date}</td></tr>
                    </table>
                    <p style="color: #666;">Log in to your vendor portal to review and respond.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">Event-AI — Pakistan's Event Planning Marketplace</p>
                </div>
                """,
            ),
        }

        return templates.get(
            event_type,
            (f"Notification: {event_type}", f"<p>{event_name} - {event_date}</p>"),
        )


email_service = EmailService()
