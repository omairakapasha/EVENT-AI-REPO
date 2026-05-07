"""
Authentication endpoints.

Routes
------
POST /auth/register              — create account, return JWT pair
POST /auth/login                 — OAuth2 form-encoded login (Swagger UI / machine clients)
POST /users/login                — JSON login used by the user portal
GET  /auth/me                    — return authenticated user profile
POST /auth/refresh               — rotate refresh token
POST /auth/logout                — revoke refresh token
POST /auth/password-reset-request
POST /auth/password-reset-confirm
GET  /auth/google                — initiate Google OAuth2 flow
GET  /auth/google/callback       — handle Google OAuth2 callback
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_settings, get_session
from src.models.user import User, RefreshToken, PasswordResetToken
from src.services.auth_service import auth_service
from src.services.google_oauth_service import google_oauth_service
from src.services.otp_service import otp_service
from src.models.email_otp import EmailOTP
from src.schemas.auth import (
    UserRegister,
    UserLogin,
    JsonLoginRequest,
    UserTokenData,
    LoginResponse,
    Token,
    UserRead,
    RefreshTokenRequest,
    LogoutRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordResetTokenResponse,
    SuccessResponse,
)
from ...middleware.rate_limit import rate_limit_dependency
from ...middleware.login_rate_limit import create_login_rate_limit_dependency
import structlog

log = structlog.get_logger()

# ── Routers ───────────────────────────────────────────────────────────────────
# /auth/* — standard auth operations
router = APIRouter(prefix="/auth", tags=["Authentication"])

# /users/* — user-portal-facing endpoints (matches frontend API calls)
users_router = APIRouter(prefix="/users", tags=["Users"])

# ── Rate limiter instances ────────────────────────────────────────────────────
register_limiter = rate_limit_dependency(max_attempts=10, window_seconds=3600)   # 10/hour
login_limiter = create_login_rate_limit_dependency(max_attempts=5, window_seconds=900)  # 5/15 min
password_reset_limiter = rate_limit_dependency(max_attempts=5, window_seconds=3600)     # 5/hour

# ── Cookie helpers ──────────────────────────────────────────────────────────
def _set_auth_cookies(response: Response, tokens: dict) -> None:
    """Set httpOnly auth cookies on a response."""
    settings = get_settings()
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=tokens["expires_in"],
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
    )

def _clear_auth_cookies(response: Response) -> None:
    """Clear httpOnly auth cookies."""
    for key in ("access_token", "refresh_token"):
        response.delete_cookie(key=key, samesite="lax")


# ─────────────────────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_limiter)],
    summary="Register a new user account",
)
async def register(
    request: Request,
    user_in: UserRegister,
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new user account and immediately issue a JWT + refresh token pair.

    - Rejects duplicate emails with 409.
    - Default role is 'user'; pass role='admin' only from trusted internal tooling.
    """
    client_ip = request.client.host if request.client else "unknown"

    existing = await session.execute(select(User).where(User.email == user_in.email))
    if existing.scalar_one_or_none():
        log.info("auth.register.duplicate", email=user_in.email, ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT_EMAIL_EXISTS", "message": "Email already registered"},
        )

    user = User(
        email=user_in.email,
        password_hash=auth_service.hash_password(user_in.password),
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        role=user_in.role or "user",
        is_active=True,
        email_verified=False,
    )
    session.add(user)
    await session.flush()

    tokens = await auth_service.create_tokens(session, user)
    await session.commit()

    # Issue OTP and send verification email (fire-and-forget)
    display_name = f"{user_in.first_name or ''} {user_in.last_name or ''}".strip() or user_in.email
    await otp_service.issue_otp(session, user.id, user.email, display_name)

    log.info("auth.register.success", user_id=str(user.id), email=user.email, ip=client_ip)

    response = JSONResponse(content=tokens)
    _set_auth_cookies(response, tokens)
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Email OTP Verification
# ─────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel as _BaseModel
from ...api.deps import get_current_user as _get_current_user

class OTPVerifyRequest(_BaseModel):
    code: str


@router.post(
    "/verify-email",
    summary="Verify email with 6-digit OTP",
)
async def verify_email(
    body: OTPVerifyRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(_get_current_user),
):
    """Verify the authenticated user's email using a 6-digit OTP."""
    await otp_service.verify_otp(session, current_user.id, body.code)

    current_user.email_verified = True
    await session.commit()

    log.info("auth.email_verified", user_id=str(current_user.id), email=current_user.email)
    return {"success": True, "data": {"message": "Email verified successfully."}, "meta": {}}


@router.post(
    "/resend-otp",
    summary="Resend email verification OTP",
)
async def resend_otp(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(_get_current_user),
):
    """Resend a new OTP to the authenticated user's email."""
    if current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMAIL_ALREADY_VERIFIED", "message": "Email is already verified."},
        )

    display_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.email
    await otp_service.issue_otp(session, current_user.id, current_user.email, display_name)

    log.info("auth.otp_resent", user_id=str(current_user.id), email=current_user.email)
    return {"success": True, "data": {"message": "Verification code sent."}, "meta": {}}


# ─────────────────────────────────────────────────────────────────────────────
# OAuth2 form-encoded login  (Swagger UI / machine clients)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=Token,
    summary="Login (OAuth2 form-encoded — for Swagger UI and machine clients)",
)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(login_limiter),
):
    """
    OAuth2 password grant: authenticate with email + password sent as
    `application/x-www-form-urlencoded` (username = email).

    - Increments failed_login_attempts on failure.
    - Locks account for 15 minutes after 5 consecutive failures.
    - Resets counter and updates last_login_at on success.
    """
    client_ip = request.client.host if request.client else "unknown"

    result = await session.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not auth_service.verify_password(form_data.password, user.password_hash):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            await session.commit()

        log.warning(
            "auth.login.failed",
            email=form_data.username,
            ip=client_ip,
            attempts=user.failed_login_attempts if user else 0,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_INVALID_CREDENTIALS", "message": "Incorrect email or password"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        log.warning("auth.login.locked", user_id=str(user.id), ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUTH_ACCOUNT_LOCKED",
                "message": "Account locked due to multiple failed login attempts. Try again in 15 minutes.",
            },
        )

    user.failed_login_attempts = 0
    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()

    tokens = await auth_service.create_tokens(session, user)
    await session.commit()

    log.info("auth.login.success", user_id=str(user.id), email=user.email, ip=client_ip)

    response = JSONResponse(content=tokens)
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=tokens["expires_in"],
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
    )
    return response


# ─────────────────────────────────────────────────────────────────────────────
# JSON login  (user portal — POST /api/v1/users/login)
# ─────────────────────────────────────────────────────────────────────────────

@users_router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login (JSON body — used by the user portal)",
)
async def json_login(
    request: Request,
    body: JsonLoginRequest,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(login_limiter),
):
    """
    JSON-body login endpoint consumed by the Next.js user portal.

    Accepts `{ email, password }` and returns the standardised envelope:

        {
          "success": true,
          "data": {
            "token": "<access_jwt>",
            "refresh_token": "<refresh_token>",
            "expires_in": 900,
            "user": { id, email, first_name, last_name, role, ... }
          }
        }

    Applies the same account-locking logic as the OAuth2 form-encoded endpoint.
    """
    client_ip = request.client.host if request.client else "unknown"

    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not auth_service.verify_password(body.password, user.password_hash):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            await session.commit()

        log.warning(
            "auth.json_login.failed",
            email=body.email,
            ip=client_ip,
            attempts=user.failed_login_attempts if user else 0,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_INVALID_CREDENTIALS", "message": "Incorrect email or password"},
        )

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        log.warning("auth.json_login.locked", user_id=str(user.id), ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUTH_ACCOUNT_LOCKED",
                "message": "Account locked due to multiple failed login attempts. Try again in 15 minutes.",
            },
        )

    user.failed_login_attempts = 0
    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()

    tokens = await auth_service.create_tokens(session, user)
    await session.commit()

    user_data = UserTokenData.model_validate(user)

    log.info("auth.json_login.success", user_id=str(user.id), email=user.email, ip=client_ip)

    response = LoginResponse(
        success=True,
        data={
            "token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "expires_in": tokens["expires_in"],
            "user": user_data.model_dump(),
        },
    )
    _set_auth_cookies(response, tokens)
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Current user profile
# ─────────────────────────────────────────────────────────────────────────────

from ...api.deps import get_current_user as auth_get_current_user


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get authenticated user profile",
)
async def me(
    current_user: User = Depends(auth_get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return the profile of the currently authenticated user."""
    user = await session.get(User, current_user.id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_CREDENTIALS_INVALID", "message": "User not found or inactive"},
        )
    return user


# ─────────────────────────────────────────────────────────────────────────────
# Token refresh
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=Token,
    dependencies=[Depends(rate_limit_dependency(max_attempts=30, window_seconds=60))],
    summary="Rotate refresh token",
)
async def refresh_token(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    Reads refresh token from httpOnly cookie. The old refresh token is immediately revoked (rotation).
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_UNAUTHORIZED", "message": "No refresh token found"},
        )
    tokens = await auth_service.rotate_refresh_token(session, refresh_token)
    response = Token(**tokens)
    response_obj = JSONResponse(content=response.model_dump())
    _set_auth_cookies(response_obj, tokens)
    return response_obj


# ─────────────────────────────────────────────────────────────────────────────
# Logout
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    response_model=SuccessResponse,
    summary="Logout — revoke refresh token",
)
async def logout(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Revoke the refresh token from httpOnly cookie, ending the session."""
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await auth_service.revoke_refresh_token(session, refresh_token)
    response = SuccessResponse(message="Logged out successfully")
    _clear_auth_cookies(response)
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Password reset
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/password-reset-request",
    response_model=PasswordResetTokenResponse,
    dependencies=[Depends(password_reset_limiter)],
    summary="Request a password reset token",
)
async def request_password_reset(
    request: Request,
    body: PasswordResetRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Request a one-time password reset token.

    Always returns 200 even for unregistered emails to prevent user enumeration.
    In production, integrate an email service to deliver the token instead of
    returning it in the response body.
    """
    client_ip = request.client.host if request.client else "unknown"

    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None:
        log.info("auth.password_reset.unregistered", email=body.email, ip=client_ip)
        return PasswordResetTokenResponse(
            token="dummy_token_for_security",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            user_email=body.email,
        )

    raw_token, expires_at = await auth_service.create_password_reset_token(session, user)

    log.info(
        "auth.password_reset.token_dev",
        user_id=str(user.id),
        email=user.email,
        token=raw_token,
        expires_at=expires_at.isoformat(),
    )

    # TODO: In production, call EmailService.send_password_reset(user.email, raw_token)

    return PasswordResetTokenResponse(
        token=raw_token,
        expires_at=expires_at,
        user_email=user.email,
    )


@router.post(
    "/password-reset-confirm",
    response_model=SuccessResponse,
    summary="Confirm password reset",
)
async def confirm_password_reset(
    body: PasswordResetConfirm,
    session: AsyncSession = Depends(get_session),
):
    """Validate the reset token and update the password. Invalidates all active sessions."""
    user = await auth_service.verify_and_consume_password_reset_token(session, body.token)
    await auth_service.reset_password(session, user, body.new_password)
    return SuccessResponse(message="Password reset successfully")


# ─────────────────────────────────────────────────────────────────────────────
# Google OAuth 2.0
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/google",
    status_code=status.HTTP_302_FOUND,
    summary="Initiate Google OAuth2 sign-in",
    description=(
        "Redirects the browser to Google's consent screen. "
        "A signed state JWT is embedded in the redirect URL for CSRF protection. "
        "Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to be configured."
    ),
)
async def google_login(redirect_to: str = "/dashboard", frontend_origin: str = ""):
    """
    Build the Google authorization URL and redirect the browser to it.

    Query Parameters
    ----------------
    redirect_to:
        Frontend path to redirect to after a successful login (default: /dashboard).
        Embedded in the signed state JWT so it survives the OAuth round-trip.
    frontend_origin:
        The portal origin that initiated the login (e.g. http://localhost:3003).
        Embedded in state JWT so the callback redirects to the correct portal.
        Defaults to FRONTEND_URL env var if not provided.
    """
    authorization_url = google_oauth_service.build_authorization_url(
        redirect_to=redirect_to,
        frontend_origin=frontend_origin,
    )
    log.info("google_oauth.redirect", redirect_to=redirect_to, frontend_origin=frontend_origin)
    return RedirectResponse(url=authorization_url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/google/callback",
    status_code=status.HTTP_302_FOUND,
    summary="Google OAuth2 callback",
    description=(
        "Handles the callback from Google after the user grants consent. "
        "Exchanges the authorization code for tokens, upserts the user, "
        "issues application JWTs, and redirects to the frontend with the token."
    ),
)
async def google_callback(
    request: Request,
    session: AsyncSession = Depends(get_session),
    code: str = None,
    state: str = None,
    error: str = None,
):
    """
    Google OAuth2 callback handler.

    Success path
    ------------
    1. Verify state JWT (CSRF check)
    2. Exchange code for Google tokens
    3. Fetch Google userinfo (enforce email_verified)
    4. Upsert user in DB
    5. Issue app JWT + refresh token
    6. Redirect to {frontend_url}{redirect_to}?token=...&refresh_token=...

    Error path
    ----------
    If Google returns an error (e.g. user denied consent), redirect to the
    frontend login page with an error query parameter.
    """
    settings = get_settings()
    frontend_login = f"{settings.frontend_url}/login"

    # ── User denied consent or Google returned an error ───────────────────────
    if error:
        log.warning("google_oauth.callback.error", error=error, ip=request.client.host if request.client else "unknown")
        return RedirectResponse(
            url=f"{frontend_login}?error=google_auth_denied",
            status_code=status.HTTP_302_FOUND,
        )

    # ── Missing code or state — likely a direct browser hit ───────────────────
    if not code or not state:
        log.warning("google_oauth.callback.missing_params", ip=request.client.host if request.client else "unknown")
        return RedirectResponse(
            url=f"{frontend_login}?error=invalid_callback",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        tokens, redirect_to, frontend_origin = await google_oauth_service.handle_callback(
            session=session,
            code=code,
            state=state,
        )
    except HTTPException as exc:
        # Map known error codes to user-friendly frontend error params
        error_code = "auth_error"
        if isinstance(exc.detail, dict):
            error_code = exc.detail.get("code", "auth_error").lower()

        log.warning(
            "google_oauth.callback.handled_error",
            code=error_code,
            status=exc.status_code,
        )
        return RedirectResponse(
            url=f"{frontend_login}?error={error_code}",
            status_code=status.HTTP_302_FOUND,
        )

    # ── Success — set httpOnly cookies and redirect ───────────────────────
    # Use frontend_origin from state JWT (set by the portal that initiated login)
    # so each portal (vendor:3000, admin:3002, user:3003) gets redirected correctly.
    origin = frontend_origin or settings.frontend_url

    # Redirect to the /auth/callback page which will verify auth and redirect to dashboard
    redirect_url = f"{origin}/auth/callback"

    log.info("google_oauth.callback.redirecting", redirect_to="/auth/callback", origin=origin)
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    _set_auth_cookies(response, tokens)
    return response
