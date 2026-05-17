"""
Pydantic Schemas for JWT Authentication API.
These schemas define request/response contracts for all auth endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID


# ============================================
# User Registration & Profile
# ============================================

class UserRegister(BaseModel):
    """Request body for user registration."""
    email: EmailStr = Field(..., description="User's email address (must be unique)")
    password: str = Field(
        ...,
        min_length=12,
        description="Password: min 12 chars, includes uppercase, lowercase, digit, special char"
    )
    first_name: Optional[str] = Field(None, max_length=100, description="User's first name")
    last_name: Optional[str] = Field(None, max_length=100, description="User's last name")
    role: Optional[str] = Field("user", max_length=50, description="Role: user, admin, or vendor")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@example.com",
            "password": "Str0ng!Pass#123",
            "first_name": "Ali",
            "last_name": "Khan",
            "role": "user"
        }
    })


class UserLogin(BaseModel):
    """OAuth2 password grant form fields."""
    username: EmailStr = Field(..., description="Email address (OAuth2 'username' field)")
    password: str = Field(..., description="User password")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "username": "user@example.com",
            "password": "Str0ng!Pass#123"
        }
    })


class UserRead(BaseModel):
    """Public user profile (no sensitive fields)."""
    id: UUID
    email: EmailStr
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_active: bool
    email_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "first_name": "Ali",
            "last_name": "Khan",
            "role": "user",
            "is_active": True,
            "email_verified": False,
            "last_login_at": "2026-04-09T10:30:00Z",
            "created_at": "2026-04-08T14:22:00Z"
        }
    })


# ============================================
# Tokens (Access + Refresh)
# ============================================

class Token(BaseModel):
    """OAuth2 token response."""
    access_token: str = Field(..., description="JWT access token (short-lived)")
    token_type: str = Field("bearer", description="Token type; always 'bearer'")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    refresh_token: str = Field(..., description="Refresh token (long-lived)")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_in": 900,
            "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4..."
        }
    })


class RefreshTokenRequest(BaseModel):
    """Request to refresh an access token."""
    refresh_token: str = Field(..., description="Valid, non-revoked refresh token")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4..."
        }
    })


class LogoutRequest(BaseModel):
    """Request to log out (revoke refresh token)."""
    refresh_token: str = Field(..., description="Refresh token to invalidate")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4..."
        }
    })


# ============================================
# Password Reset
# ============================================

class PasswordResetRequest(BaseModel):
    """Request to initiate password reset."""
    email: EmailStr = Field(..., description="Registered user's email")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@example.com"
        }
    })


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with token and new password."""
    token: str = Field(..., description="One-time password reset token")
    new_password: str = Field(
        ...,
        min_length=12,
        description="New password: min 12 chars with complexity requirements"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "token": "cmVzdXNfY2hhbmdlX3Rva2VuX3Rva2VuX3Rva2Vu...",
            "new_password": "N3wStr0ng!Pass#456"
        }
    })


class PasswordResetTokenResponse(BaseModel):
    """
    DEPRECATED: No longer used by any endpoint as of the password-reset-token-exposure fix.
    The token is now delivered exclusively via email. Do not use in new code.
    Retained temporarily to avoid breaking any existing tests that reference this schema.
    """
    token: str = Field(..., description="Raw password reset token")
    expires_at: datetime = Field(..., description="Token expiry timestamp")
    user_email: EmailStr = Field(..., description="Email of the user")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "token": "cmVzdXNfY2hhbmdlX3Rva2VuX3Rva2VuX3Rva2Vu...",
            "expires_at": "2026-04-09T11:00:00Z",
            "user_email": "user@example.com"
        }
    })


# ============================================
# Standardized API Envelope
# ============================================

class SuccessResponse(BaseModel):
    """Generic success response for operations with no data."""
    success: bool = Field(True, description="Always true for success")
    message: str = Field(..., description="Human-readable success message")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "message": "Password reset email sent"
        }
    })


# ============================================
# JSON Login (used by user portal)
# ============================================

class JsonLoginRequest(BaseModel):
    """JSON body login — used by the user portal (email + password)."""
    email: EmailStr = Field(..., description="Registered user email")
    password: str = Field(..., description="User password")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@example.com",
            "password": "Str0ng!Pass#123",
        }
    })


class UserTokenData(BaseModel):
    """Minimal user payload embedded in the login response."""
    id: UUID
    email: EmailStr
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_active: bool
    email_verified: bool

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    """
    Response shape expected by the user portal:
      { success: true, data: { token, refresh_token, expires_in, user } }
    """
    success: bool = Field(True)
    data: dict = Field(..., description="Contains token, refresh_token, expires_in, user")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
                "expires_in": 900,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "first_name": "Ali",
                    "last_name": "Khan",
                    "role": "user",
                    "is_active": True,
                    "email_verified": False,
                },
            },
        }
    })


# ============================================
# Google OAuth state / PKCE
# ============================================

class OAuthStatePayload(BaseModel):
    """
    Signed state token payload for Google OAuth CSRF protection.
    Encoded as a short-lived JWT and passed as the `state` query param.
    """
    nonce: str = Field(..., description="Random nonce to prevent replay")
    redirect_to: str = Field(default="/dashboard", description="Post-login redirect path")
    iat: datetime = Field(default_factory=lambda: datetime.now())
    exp: datetime


# Export all schemas
__all__ = [
    "UserRegister",
    "UserLogin",
    "JsonLoginRequest",
    "UserTokenData",
    "LoginResponse",
    "OAuthStatePayload",
    "UserRead",
    "Token",
    "RefreshTokenRequest",
    "LogoutRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "SuccessResponse",
]
