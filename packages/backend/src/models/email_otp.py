"""
EmailOTP model — stores 6-digit OTP codes for email verification.
Each OTP is single-use, expires in 10 minutes, and is hashed at rest.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import DateTime


def _utcnow() -> datetime:
    return datetime.utcnow()


class EmailOTP(SQLModel, table=True):
    __tablename__ = "email_otps"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    # SHA-256 hash of the 6-digit code — never store plaintext
    code_hash: str = Field(max_length=64)
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    used_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    created_at: datetime = Field(
        default_factory=_utcnow, sa_column=Column(DateTime(timezone=True))
    )
