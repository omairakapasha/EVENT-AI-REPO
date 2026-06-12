"""
Dependency injection helpers for API routes.
"""
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.services.auth_service import auth_service
from src.services.event_bus_service import event_bus, EventBusService
from src.models.user import User

# OAuth2 scheme — token endpoint is /api/v1/auth/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
# HTTPBearer for extracting Bearer token (auto_error=False so we can fall back to cookie)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    FastAPI dependency that extracts JWT from Authorization header or httpOnly cookie,
    validates it, and returns the authenticated User.

    Token resolution order:
    1. Authorization: Bearer <token> header (API clients, Swagger UI)
    2. access_token httpOnly cookie (browser portals)

    Raises HTTPException(401) on failure.
    """
    token: Optional[str] = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_UNAUTHORIZED", "message": "Not authenticated"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_service.verify_access_token(token, session)

    if not user.email_verified:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "AUTH_EMAIL_NOT_VERIFIED",
                "message": "Email address has not been verified.",
            },
        )

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that ensures the current user has admin role.
    Raises HTTPException(403) if user is not an admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires administrator privileges"
        )
    return current_user

def get_event_bus() -> EventBusService:
    """Dependency injection for the domain event bus."""
    return event_bus


def get_http_client(request: Request) -> httpx.AsyncClient:
    """
    FastAPI dependency that returns the shared httpx.AsyncClient from app.state.

    The client is initialised in the FastAPI lifespan (database.py) and stored
    on app.state.http_client. Routes use Depends(get_http_client) instead of
    accessing request.app.state.http_client directly.
    """
    return request.app.state.http_client
