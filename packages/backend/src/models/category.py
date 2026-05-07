from datetime import datetime, timezone
import uuid
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class VendorCategoryLink(SQLModel, table=True):
    __tablename__ = "vendor_categories"
    
    vendor_id: uuid.UUID = Field(foreign_key="vendors.id", primary_key=True)
    category_id: uuid.UUID = Field(foreign_key="categories.id", primary_key=True)

class Category(SQLModel, table=True):
    __tablename__ = "categories"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(unique=True, index=True)
    description: Optional[str] = None
    icon_url: Optional[str] = None
    display_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    vendors: List["Vendor"] = Relationship(back_populates="categories", link_model=VendorCategoryLink)
