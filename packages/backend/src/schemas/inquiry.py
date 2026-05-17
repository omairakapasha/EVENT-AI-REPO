"""
Customer Inquiry schemas for vendor marketplace.
"""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from ..models.inquiry import InquiryStatus


class CustomerInquiryBase(BaseModel):
    customer_name: str = Field(..., max_length=255)
    customer_email: EmailStr
    customer_phone: Optional[str] = Field(None, max_length=50)
    message: str = Field(..., max_length=5000)
    preferred_date: Optional[datetime] = None
    event_type: Optional[str] = Field(None, max_length=100)
    expected_guests: Optional[int] = None
    budget_range: Optional[str] = Field(None, max_length=100)


class CustomerInquiryCreate(CustomerInquiryBase):
    pass


class CustomerInquiryUpdate(BaseModel):
    status: Optional[InquiryStatus] = None
    vendor_response: Optional[str] = Field(None, max_length=5000)


class CustomerInquiryRead(CustomerInquiryBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vendor_id: uuid.UUID
    status: InquiryStatus
    vendor_response: Optional[str] = None
    vendor_responded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
