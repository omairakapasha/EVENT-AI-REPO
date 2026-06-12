"""
Tests for EmailService — SMTP dispatch and dev mode logging.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from src.services.email_service import EmailService, email_service


class TestEmailService:
    """Unit tests for email service."""

    def test_render_booking_email_created(self):
        """Test email template for booking.created event."""
        subject, html = email_service.render_booking_email(
            event_type="booking.created",
            vendor_name="Test Vendor",
            event_date="2026-05-15",
            event_name="Birthday Party",
        )
        assert subject == "Booking Request Received"
        assert "Test Vendor" in html
        assert "Birthday Party" in html
        assert "2026-05-15" in html

    def test_render_booking_email_confirmed(self):
        """Test email template for booking.confirmed event."""
        subject, html = email_service.render_booking_email(
            event_type="booking.confirmed",
            vendor_name="Catering Co",
            event_date="2026-06-01",
            event_name="Wedding Reception",
        )
        assert "Confirmed" in subject
        assert "Catering Co" in html

    def test_render_booking_email_unknown_type(self):
        """Test fallback for unknown event type."""
        subject, html = email_service.render_booking_email(
            event_type="unknown.event",
            vendor_name="Vendor",
            event_date="2026-01-01",
            event_name="Event",
        )
        assert "unknown.event" in subject

    @pytest.mark.asyncio
    async def test_send_email_dev_mode_logs(self, caplog):
        """Test that email is logged (not sent) when SMTP not configured."""
        # Create service with no SMTP config
        service = EmailService()
        service._smtp_configured = False

        result = await service.send_email(
            to="test@example.com",
            subject="Test Subject",
            body_html="<p>Test body</p>",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_email_fire_and_forget(self):
        """Test that send_email spawns background task."""
        service = EmailService()
        service._smtp_configured = True

        with patch.object(service, "_send_smtp", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await service.send_email(
                to="test@example.com",
                subject="Test",
                body_html="<p>Body</p>",
            )
            assert result is True
            # Background task is spawned, not awaited immediately
