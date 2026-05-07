import uuid
from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Relationship
import enum
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import ENUM
from .category import VendorCategoryLink


def _utcnow() -> datetime:
    """Return current UTC time as a naive datetime (matches TIMESTAMP WITHOUT TIME ZONE columns)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

class VendorStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REJECTED = "REJECTED"

class Vendor(SQLModel, table=True):
    __tablename__ = "vendors"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", unique=True, index=True)
    
    business_name: str = Field(index=True)
    description: Optional[str] = None
    contact_email: str = Field(unique=True, index=True)
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    
    city: Optional[str] = Field(index=True)
    region: Optional[str] = Field(index=True)
    
    status: VendorStatus = Field(
        sa_column=Column(ENUM(VendorStatus, name="vendor_status_enum", create_type=False)),
        default=VendorStatus.PENDING
    )
    
    rating: float = Field(default=0.0)
    total_reviews: int = Field(default=0)
    
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    
    # Relationships
    categories: List["Category"] = Relationship(back_populates="vendors", link_model=VendorCategoryLink)
    services: List["Service"] = Relationship(back_populates="vendor")
    approvals: List["ApprovalRequest"] = Relationship(back_populates="vendor")
    inquiries: List["CustomerInquiry"] = Relationship(back_populates="vendor")
