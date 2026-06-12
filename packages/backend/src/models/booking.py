from datetime import date, datetime, time
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
from sqlmodel import SQLModel, Field, Column, String, JSON

# ============================================
# Enums
# ============================================

class BookingStatus(str, Enum):
    pending = "pending"
    quoted = "quoted"
    negotiating = "negotiating"
    accepted = "accepted"
    awaiting_deposit = "awaiting_deposit"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    rejected = "rejected"
    no_show = "no_show"

class PaymentStatus(str, Enum):
    pending = "pending"
    partial = "partial"
    paid = "paid"
    refunded = "refunded"
    failed = "failed"

class SenderType(str, Enum):
    vendor = "vendor"
    client = "client"
    system = "system"

# ============================================
# Bookings
# ============================================

class BookingBase(SQLModel):
    vendor_id: uuid.UUID
    service_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    
    # Event details
    event_id: Optional[uuid.UUID] = None
    event_name: Optional[str] = None
    event_date: date
    event_start_time: Optional[time] = None
    event_end_time: Optional[time] = None
    event_location: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    
    # Client info
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    guest_count: Optional[int] = None
    
    # Booking details
    status: BookingStatus = Field(default=BookingStatus.pending)
    quantity: int = Field(default=1)
    special_requirements: Optional[str] = None
    notes: Optional[str] = None
    
    # Pricing
    unit_price: float
    total_price: float
    currency: str = Field(default="PKR", max_length=3)
    
    # Payment
    payment_status: PaymentStatus = Field(default=PaymentStatus.pending)
    deposit_amount: Optional[float] = None
    deposit_paid_at: Optional[datetime] = None
    
    # Workflow
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[uuid.UUID] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[uuid.UUID] = None
    cancellation_reason: Optional[str] = None
    
    metadata_info: Dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON))

class Booking(BookingBase, table=True):
    __tablename__ = "bookings"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

# API Parsing Models
class BookingCreate(BookingBase):
    # unit_price and total_price are computed by the service from the service
    # catalogue — the frontend never sends them.  Make them optional here so
    # Pydantic validation passes; booking_service.create_booking() overwrites
    # them with the correct values anyway.
    unit_price: float = 0.0
    total_price: float = 0.0

    model_config = {"populate_by_name": True}  # accept snake_case from DB reads

class BookingRead(BookingBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

# ============================================
# Booking Messages
# ============================================

class BookingMessageBase(SQLModel):
    booking_id: uuid.UUID
    sender_id: Optional[uuid.UUID] = None
    sender_type: SenderType
    message: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    is_read: bool = Field(default=False)
    read_at: Optional[datetime] = None

class BookingMessage(BookingMessageBase, table=True):
    __tablename__ = "booking_messages"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class BookingMessageCreate(BookingMessageBase):
    pass

class BookingMessageRead(BookingMessageBase):
    id: uuid.UUID
    created_at: datetime
