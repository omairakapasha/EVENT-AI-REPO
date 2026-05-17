import uuid
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from ..models.approval import ApprovalType, ApprovalStatus

class ApprovalRequestBase(BaseModel):
    type: ApprovalType
    data_snapshot: Dict[str, Any] = {}
    decision_notes: Optional[str] = None

class ApprovalRequestCreate(ApprovalRequestBase):
    vendor_id: uuid.UUID

class ApprovalRequestUpdate(BaseModel):
    status: ApprovalStatus
    decision_notes: Optional[str] = None

class ApprovalRequestRead(ApprovalRequestBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vendor_id: uuid.UUID
    status: ApprovalStatus
    reviewed_by: Optional[uuid.UUID] = None
    submitted_date: datetime
    reviewed_date: Optional[datetime] = None
