import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Relationship
import enum
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import ENUM, JSONB


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class ApprovalType(str, enum.Enum):
    NEW_REGISTRATION = "NEW_REGISTRATION"
    PROFILE_EDIT = "PROFILE_EDIT"

class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MORE_INFO = "MORE_INFO"

class ApprovalRequest(SQLModel, table=True):
    __tablename__ = "approval_requests"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    vendor_id: uuid.UUID = Field(foreign_key="vendors.id", index=True)
    
    type: ApprovalType = Field(
        sa_column=Column(ENUM(ApprovalType, name="approval_type_enum", create_type=False))
    )
    status: ApprovalStatus = Field(
        sa_column=Column(ENUM(ApprovalStatus, name="approval_status_enum", create_type=False)),
        default=ApprovalStatus.PENDING
    )
    
    data_snapshot: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    decision_notes: Optional[str] = None
    reviewed_by: Optional[uuid.UUID] = Field(foreign_key="users.id", nullable=True)
    
    submitted_date: datetime = Field(default_factory=_utcnow)
    reviewed_date: Optional[datetime] = None
    
    vendor: "Vendor" = Relationship(back_populates="approvals")
