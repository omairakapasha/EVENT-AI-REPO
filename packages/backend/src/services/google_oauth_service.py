"""
Google OAuth 2.0 service.

Responsibilities
----------------
- Build the Google authorization URL with a signed state JWT for CSRF protection
- Exchange the authorization code for Google access + id tokens
- Fetch the authenticated user's profile from Google's userinfo endpoint
- Upsert the user record in the database (create on first login, update on subsequent)
- Issue application JWT + refresh token pair

OAuth 2.0 Flow
--------------
  1. GET  /api/v1/auth/google
         → generate signed state JWT
         → 302 redirect to Google consent screen

  2. GET  /api/v1/auth/google/callback?code=...&state=...
         → verify state JWT (CSRF check)
         → POST to Google token endpoint to exchange code
         → GET Google userinfo with access token
         → upsert user in DB
         → issue app JWT + refresh token
         → 302 redirect to {frontend_url}/dashboard?token=...&refresh_token=...

Security considerations
-----------------------
- State parameter is a short-lived signed JWT (5 min TTL) — prevents CSRF
- Google email_verified is enforced — unverified Google accounts are rejected
- New OAuth users get an unusable random password hash — they cannot log in
  with a password unless they explicitly go through the password-reset flow
- Inactive users are rejected at the upsert step
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_settings
from src.models.user import User
from src.services.auth_service import auth_service

log = structlog.get_logger()

# ── Google OAuth 2.0 public endpoints ─────────────────────────────────────────
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Scopes: openid identity + email + basic profile
_GOOGLE_SCOPES = "openid email profile"

# State JWT lives only long enough for the browser round-trip
_STATE_JWT_TTL_SECONDS = 300  # 5 minutes


class GoogleOAuthService:
    """
    Encapsulates all Google OAuth 2.0 logic.
    Instantiated once as a module-level singleton.
    """

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _settings():
        """Lazy settings access so the singleton can be imported at module level."""
        return get_settings()

    def _require_configured(self) -> None:
        """Raise 503 if Google OAuth credentials are not set in the environment."""
        s = self._settings()
        if not s.google_client_id or not s.google_client_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "OAUTH_NOT_CONFIGURED",
                    "message": (
                        "Google Sign-In is not configured on this server. "
                        "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in the environment."
                    ),
                },
            )

    # ── State JWT (CSRF protection) ───────────────────────────────────────────

    def create_state_token(self, redirect_to: str = "/dashboard", frontend_origin: str = "") -> str:
        """
        Create a signed, short-lived JWT to use as the OAuth `state` parameter.

        The state JWT contains:
          - nonce: random 16-byte URL-safe string (prevents replay)
          - redirect_to: frontend path to redirect after successful login
          - frontend_origin: the portal origin (e.g. http://localhost:3000) to redirect back to
          - iat / exp: issued-at and expiry (5 min)
          - iss: "event-ai-oauth" (distinguishes from access tokens)

        Signed with the same JWT_SECRET_KEY as access tokens but with a
        different `iss` claim so they cannot be confused.
        """
        s = self._settings()
        now = datetime.now(timezone.utc)
        payload = {
            "nonce": secrets.token_urlsafe(16),
            "redirect_to": redirect_to,
            "frontend_origin": frontend_origin or s.frontend_url,
            "iat": now,
            "exp": now + timedelta(seconds=_STATE_JWT_TTL_SECONDS),
            "iss": "event-ai-oauth",
        }
        return jwt.encode(payload, s.jwt_secret_key, algorithm=s.jwt_algorithm)

    def verify_state_token(self, state: str) -> dict:
        """
        Decode and validate the state JWT received in the OAuth callback.

        Raises HTTPException(400) if the token is invalid, expired, or has
        the wrong issuer — which indicates a CSRF attempt or a stale tab.
        """
        s = self._settings()
        try:
            payload = jwt.decode(
                state,
                s.jwt_secret_key,
                algorithms=[s.jwt_algorithm],
                issuer="event-ai-oauth",
            )
            return payload
        except JWTError as exc:
            log.warning("google_oauth.state.invalid", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "OAUTH_INVALID_STATE",
                    "message": (
                        "Invalid or expired OAuth state parameter. "
                        "This may be a CSRF attempt or the sign-in session timed out. "
                        "Please try signing in again."
                    ),
                },
            ) from exc

    # ── Authorization URL ─────────────────────────────────────────────────────

    def build_authorization_url(self, redirect_to: str = "/dashboard", frontend_origin: str = "") -> str:
        """
        Build the full Google OAuth2 authorization URL.

        Parameters
        ----------
        redirect_to:
            Frontend path to redirect the user to after a successful login.
            Embedded in the signed state JWT.
        frontend_origin:
            The portal origin (e.g. http://localhost:3000) that initiated the
            OAuth flow. Embedded in state JWT so the callback redirects to the
            correct portal. Defaults to settings.frontend_url if not provided.

        Returns
        -------
        str
            The URL to redirect the browser to.
        """
        self._require_configured()
        s = self._settings()

        state = self.create_state_token(redirect_to=redirect_to, frontend_origin=frontend_origin)
        params = {
            "client_id": s.google_client_id,
            "redirect_uri": s.google_redirect_uri,
            "response_type": "code",
            "scope": _GOOGLE_SCOPES,
            "state": state,
            # access_type=offline requests a refresh token from Google (not used
            # by us directly, but good practice for future use)
            "access_type": "offline",
            # Always show the account picker so users can switch accounts
            "prompt": "select_account",
        }
        return f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"

    # ── Token Exchange ────────────────────────────────────────────────────────

    async def exchange_code_for_tokens(self, code: str) -> dict:
        """
        Exchange the one-time authorization code for Google access + id tokens.

        Uses a 10-second timeout to avoid hanging the request if Google is slow.
        Raises HTTPException(502) on any non-200 response from Google.
        """
        s = self._settings()
        payload = {
            "code": code,
            "client_id": s.google_client_id,
            "client_secret": s.google_client_secret,
            "redirect_uri": s.google_redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(_GOOGLE_TOKEN_URL, data=payload)

        if response.status_code != 200:
            log.error(
                "google_oauth.token_exchange.failed",
                http_status=response.status_code,
                body_preview=response.text[:300],
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "OAUTH_TOKEN_EXCHANGE_FAILED",
                    "message": "Failed to exchange authorization code with Google. Please try again.",
                },
            )

        return response.json()

    # ── ID Token Verification (google-auth library) ───────────────────────────

    def verify_google_id_token(self, id_token: str) -> dict:
        """
        Verify the Google ID token using the official `google-auth` library.

        This is the recommended approach from Google and the guide:
          - Validates the token signature against Google's public keys
          - Verifies the `aud` claim matches our CLIENT_ID (prevents token misuse)
          - Verifies the `iss` claim is accounts.google.com
          - Verifies the token has not expired
          - All done locally — no extra HTTP call to Google

        Returns the decoded token claims dict with:
          sub, email, email_verified, given_name, family_name, picture, etc.

        Raises HTTPException(401) if the token is invalid for any reason.
        """
        s = self._settings()
        try:
            idinfo = google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                s.google_client_id,
            )
        except ValueError as exc:
            log.warning("google_oauth.id_token.invalid", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "OAUTH_INVALID_ID_TOKEN",
                    "message": "Google ID token verification failed. Please try signing in again.",
                },
            ) from exc

        if not idinfo.get("email_verified", False):
            log.warning("google_oauth.id_token.unverified_email", email=idinfo.get("email"))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "OAUTH_EMAIL_NOT_VERIFIED",
                    "message": (
                        "Your Google account email address is not verified. "
                        "Please verify your email with Google and try again."
                    ),
                },
            )

        return idinfo

    # ── User Upsert ───────────────────────────────────────────────────────────

    async def get_or_create_user(self, session: AsyncSession, google_profile: dict) -> User:
        """
        Find an existing user by email or create a new one from the Google profile.

        Existing user behaviour
        -----------------------
        - Reject if is_active is False (deactivated account)
        - Set email_verified = True (Google has verified it)
        - Update last_login_at
        - Backfill first_name / last_name if they were previously empty

        New user behaviour
        ------------------
        - Create with role='user', is_active=True, email_verified=True
        - Assign a random, cryptographically strong unusable password hash so
          the account cannot be used with password-based login unless the user
          explicitly sets a password via the password-reset flow
        - flush() before creating tokens so user.id is populated

        Parameters
        ----------
        session:
            Active async SQLAlchemy session (not yet committed).
        google_profile:
            Dict returned by fetch_google_userinfo().

        Returns
        -------
        User
            The persisted (but not yet committed) User ORM instance.
        """
        email: str = google_profile["email"].lower().strip()
        first_name: Optional[str] = google_profile.get("given_name")
        last_name: Optional[str] = google_profile.get("family_name")
        now = datetime.now(timezone.utc)

        result = await session.execute(select(User).where(User.email == email))
        user: Optional[User] = result.scalar_one_or_none()

        if user:
            if not user.is_active:
                log.warning(
                    "google_oauth.login.inactive_user",
                    user_id=str(user.id),
                    email=email,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "AUTH_ACCOUNT_INACTIVE",
                        "message": (
                            "Your account has been deactivated. "
                            "Please contact support for assistance."
                        ),
                    },
                )

            # Sync fields that may have changed on Google's side
            user.email_verified = True
            user.last_login_at = now
            # Only backfill — don't overwrite names the user may have customised
            if first_name and not user.first_name:
                user.first_name = first_name
            if last_name and not user.last_name:
                user.last_name = last_name

            log.info(
                "google_oauth.login.existing_user",
                user_id=str(user.id),
                email=email,
            )
        else:
            # Generate a random unusable password so the account cannot be
            # brute-forced via the password login endpoint.
            unusable_password_hash = auth_service.hash_password(secrets.token_urlsafe(32))

            user = User(
                email=email,
                password_hash=unusable_password_hash,
                first_name=first_name,
                last_name=last_name,
                role="user",
                is_active=True,
                email_verified=True,
                last_login_at=now,
            )
            session.add(user)
            # flush to get user.id assigned before we create tokens
            await session.flush()

            log.info(
                "google_oauth.login.new_user",
                user_id=str(user.id),
                email=email,
            )

        return user

    # ── Full Callback Handler ─────────────────────────────────────────────────

    async def handle_callback(
        self,
        session: AsyncSession,
        code: str,
        state: str,
    ) -> tuple[dict, str, str]:
        """
        Orchestrate the full OAuth callback sequence:

          1. Verify state JWT (CSRF check)
          2. Exchange authorization code for Google tokens
          3. Verify the Google ID token using google-auth library
             (validates signature, aud, iss, expiry — no extra HTTP call)
          4. Upsert user in the database
          5. Issue application JWT + refresh token
          6. Commit the session
          7. Return (token_dict, redirect_to)

        Parameters
        ----------
        session:
            Active async SQLAlchemy session.
        code:
            Authorization code from Google's callback query string.
        state:
            Signed state JWT from Google's callback query string.

        Returns
        -------
        token_dict:
            {access_token, token_type, expires_in, refresh_token}
        redirect_to:
            Frontend path extracted from the state JWT (e.g. "/dashboard").
        frontend_origin:
            Portal origin from the state JWT (e.g. "http://localhost:3003").
        """
        state_payload = self.verify_state_token(state)
        redirect_to: str = state_payload.get("redirect_to", "/dashboard")
        frontend_origin: str = state_payload.get("frontend_origin", "")

        # Exchange code → get Google tokens (access_token + id_token)
        google_tokens = await self.exchange_code_for_tokens(code)

        # Verify the ID token locally using google-auth (secure, no extra HTTP call)
        # Falls back to userinfo endpoint only if id_token is absent (shouldn't happen)
        raw_id_token = google_tokens.get("id_token")
        if not raw_id_token:
            log.error("google_oauth.callback.missing_id_token")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "OAUTH_MISSING_ID_TOKEN",
                    "message": "Google did not return an ID token. Please try again.",
                },
            )

        # verify_google_id_token validates signature, aud, iss, exp, email_verified
        idinfo = self.verify_google_id_token(raw_id_token)

        # Normalise to the profile shape expected by get_or_create_user
        google_profile = {
            "email": idinfo["email"],
            "email_verified": idinfo.get("email_verified", False),
            "given_name": idinfo.get("given_name"),
            "family_name": idinfo.get("family_name"),
            "sub": idinfo["sub"],
            "picture": idinfo.get("picture"),
        }

        user = await self.get_or_create_user(session, google_profile)
        # Commit user changes (including email_verified=True) BEFORE creating tokens
        # This ensures the JWT contains the correct email_verified status
        await session.commit()
        await session.refresh(user)  # Refresh to get committed state
        tokens = await auth_service.create_tokens(session, user)

        log.info(
            "google_oauth.callback.success",
            user_id=str(user.id),
            email=user.email,
        )
        return tokens, redirect_to, frontend_origin


# Module-level singleton — import this everywhere
google_oauth_service = GoogleOAuthService()
