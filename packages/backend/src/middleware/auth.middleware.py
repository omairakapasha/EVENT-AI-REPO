"""
Authentication middleware for verifying JWT tokens and attaching user to request.
"""
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from src.services.auth_service import auth_service
from src.config.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

# Security scheme for extracting Bearer token
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session)
):
    """
    Extract and verify JWT token from Authorization header or httpOnly cookie.
    Attaches user information to request state if valid.

    Token resolution order:
    1. Authorization: Bearer <token> header (API clients, Swagger UI)
    2. access_token httpOnly cookie (browser portals)

    Args:
        request: FastAPI request object
        credentials: Bearer token credentials
        session: Database session

    Returns:
        User object if token valid, raises HTTPException otherwise
    """
    # Resolve token: prefer Bearer header, fall back to httpOnly cookie
    token: Optional[str] = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_UNAUTHORIZED", "message": "Not authenticated"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Verify token, fetch and validate user in one call
        user = await auth_service.verify_access_token(token, session)

        # Note: email_verified check removed - OAuth users are pre-verified by Google
        # For email/password users, email verification is encouraged but not enforced at middleware level

        # Attach user to request state for easy access in routes
        request.state.user = user
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Token verification failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_UNAUTHORIZED", "message": "Could not validate credentials"},
            headers={"WWW-Authenticate": "Bearer"},
        )


# Optional: Dependency that returns None if no auth (for public endpoints that can use auth)
async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> Optional[object]:
    """
    Similar to get_current_user but returns None instead of raising exception
    when no or invalid token is provided.

    Intentionally does NOT enforce the email_verified guard — unverified users
    are returned as-is so optional-auth endpoints can still serve them.
    Reads from Authorization header or httpOnly cookie.
    """
    token: Optional[str] = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        return None

    try:
        return await auth_service.verify_access_token(token, session)
    except Exception:
        return None