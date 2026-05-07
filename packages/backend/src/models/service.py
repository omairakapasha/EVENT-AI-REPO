import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Service(SQLModel, table=True):
    __tablename__ = "services"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    vendor_id: uuid.UUID = Field(foreign_key="vendors.id", index=True)
    
    name: str = Field(index=True)
    description: Optional[str] = None
    capacity: Optional[int] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    requirements: Optional[str] = None
    
    is_active: bool = Field(default=True)
    
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    
    vendor: "Vendor" = Relationship(back_populates="services")
