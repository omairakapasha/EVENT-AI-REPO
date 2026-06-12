"""
User and RefreshToken models for authentication.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field, Column, DateTime
from sqlalchemy import Boolean, Integer, String


class SubscriptionStatus(str, Enum):
    free = "free"
    pro = "pro"


class UserBase(SQLModel):
    email: str = Field(index=True, unique=True, max_length=255)
    first_name: Optional[str] = Field(max_length=100)
    last_name: Optional[str] = Field(max_length=100)
    role: str = Field(default="user", max_length=50)
    is_active: bool = Field(default=True)


class User(UserBase, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    password_hash: str = Field(max_length=255)
    email_verified: bool = Field(default=False)
    last_login_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    failed_login_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    subscription_status: SubscriptionStatus = Field(default=SubscriptionStatus.free, sa_column=Column(String(20), default="free"))
    subscription_expires_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    terms_accepted_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True), onupdate=datetime.utcnow))


class UserCreate(UserBase):
    password: str


class UserRead(SQLModel):
    id: uuid.UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_active: bool
    email_verified: bool
    last_login_at: Optional[datetime]
    subscription_status: SubscriptionStatus
    subscription_expires_at: Optional[datetime]
    terms_accepted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class RefreshTokenBase(SQLModel):
    user_id: uuid.UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    token_hash: str = Field(max_length=255)
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))


class RefreshToken(RefreshTokenBase, table=True):
    __tablename__ = "refresh_tokens"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    revoked_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True), onupdate=datetime.utcnow))


class RefreshTokenCreate(SQLModel):
    user_id: uuid.UUID
    token_hash: str
    expires_at: datetime


class RefreshTokenRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    token_hash: str
    expires_at: datetime
    revoked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# ============================================
# Password Reset Tokens
# ============================================

class PasswordResetTokenBase(SQLModel):
    user_id: uuid.UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    token_hash: str = Field(max_length=255)
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))


class PasswordResetToken(PasswordResetTokenBase, table=True):
    __tablename__ = "password_reset_tokens"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    used_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))


class PasswordResetTokenRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    token_hash: str
    expires_at: datetime
    used_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
