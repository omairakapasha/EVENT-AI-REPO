"""
Customer Inquiry model for vendor marketplace.
Represents a customer reaching out to a vendor for services.
"""
import uuid
import enum
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import ENUM


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class InquiryStatus(str, enum.Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUOTED = "QUOTED"
    CONVERTED = "CONVERTED"
    DECLINED = "DECLINED"


class CustomerInquiry(SQLModel, table=True):
    __tablename__ = "customer_inquiries"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    vendor_id: uuid.UUID = Field(foreign_key="vendors.id", index=True)
    
    # Customer contact information
    customer_name: str = Field(index=True)
    customer_email: str = Field(index=True)
    customer_phone: Optional[str] = None
    
    # Inquiry details
    message: str
    preferred_date: Optional[datetime] = None
    event_type: Optional[str] = None
    expected_guests: Optional[int] = None
    budget_range: Optional[str] = None
    
    # Status tracking
    status: InquiryStatus = Field(
        sa_column=Column(ENUM(InquiryStatus, name="inquiry_status_enum", create_type=False)),
        default=InquiryStatus.NEW
    )
    
    # Vendor response tracking
    vendor_response: Optional[str] = None
    vendor_responded_at: Optional[datetime] = None

    # Quote bridge (G1.5)
    quote_id: Optional[uuid.UUID] = Field(default=None, index=True)
    quoted_amount: Optional[float] = None

    # Metadata
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    
    # Relationships
    vendor: "Vendor" = Relationship(back_populates="inquiries")
