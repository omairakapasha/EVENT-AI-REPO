import asyncio
from contextlib import asynccontextmanager
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
import structlog

from pydantic import field_validator, EmailStr, Field

log = structlog.get_logger()

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost/postgres"
    direct_url: str | None = None

    # JWT Authentication Settings
    jwt_secret_key: str = Field(..., min_length=32, description="JWT signing secret")
    jwt_algorithm: str = Field("HS256", description="JWT signature algorithm")
    access_token_expire_minutes: int = Field(15, description="Access token TTL in minutes")
    refresh_token_expire_days: int = Field(7, description="Refresh token TTL in days")

    # CORS origins (comma-separated in env)
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3002", "http://localhost:3003", "http://localhost:3004"],
        description="Allowed CORS origins"
    )

    # Google OAuth 2.0
    google_client_id: Optional[str] = Field(default=None, description="Google OAuth2 client ID from Google Cloud Console")
    google_client_secret: Optional[str] = Field(default=None, description="Google OAuth2 client secret")
    google_redirect_uri: str = Field(
        default="http://localhost:5000/api/v1/auth/google/callback",
        description="Must exactly match the Authorized Redirect URI registered in Google Cloud Console",
    )

    # Frontend base URL — used for post-OAuth browser redirects
    frontend_url: str = Field(
        default="http://localhost:3003",
        description="User portal base URL; tokens are passed as query params after OAuth",
    )

    # Seed script settings
    seed_admin_email: Optional[str] = Field(default=None)
    seed_admin_password: Optional[str] = Field(default=None)

    # Environment — controls cookie security and other dev/prod differences
    environment: str = Field(default="development", description="Runtime environment: development | production")

    # SMTP / Email Settings
    smtp_host: Optional[str] = Field(default=None, description="SMTP server hostname")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_secure: bool = Field(default=False, description="Use TLS for SMTP connection")
    smtp_user: Optional[str] = Field(default=None, description="SMTP authentication username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP authentication password")
    email_from: str = Field(default="noreply@eventai.pk", description="Default sender email address")

    # CDN (Cloudflare R2 / AWS S3)
    cdn_provider: str = Field(default="r2", description="CDN provider: r2 or s3")
    cdn_bucket_name: str = Field(default="event-ai-uploads", description="CDN bucket name")
    cdn_public_url: Optional[str] = Field(default=None, description="CDN public base URL")
    cdn_enabled: bool = Field(default=False, description="Enable CDN uploads")
    cdn_endpoint_url: Optional[str] = Field(default=None, description="CDN S3-compatible endpoint URL")
    cdn_access_key_id: Optional[str] = Field(default=None, description="CDN access key ID")
    cdn_secret_access_key: Optional[str] = Field(default=None, description="CDN secret access key")
    cdn_region: str = Field(default="auto", description="CDN region")
    cdn_public_endpoint: Optional[str] = Field(default=None, description="CDN public endpoint for URL construction")

    # Gemini API
    gemini_api_key: Optional[str] = Field(default=None, description="Gemini API key for embedding and AI features")

    # RAG / Embedding
    gemini_embedding_model: str = Field(
        default="text-embedding-004",
        description="Gemini embedding model name",
    )
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai/",
        description="Gemini OpenAI-compatible base URL",
    )
    embedding_dimensions: int = Field(
        default=768,
        description="Number of embedding dimensions produced by the embedding model",
    )
    hybrid_trigram_weight: float = Field(
        default=0.3,
        description="Weight applied to trigram (keyword) scores in hybrid search (must sum to 1.0 with hybrid_semantic_weight)",
    )
    hybrid_semantic_weight: float = Field(
        default=0.7,
        description="Weight applied to semantic scores in hybrid search (must sum to 1.0 with hybrid_trigram_weight)",
    )

    model_config = SettingsConfigDict(
        # Look for .env in the package dir first, then fall back to the monorepo root
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            if v.startswith("postgresql://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            # Strip sslmode — asyncpg doesn't accept it as a query param.
            # SSL is passed via connect_args on the engine instead.
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            parsed = urlparse(v)
            params = parse_qs(parsed.query, keep_blank_values=True)
            params.pop("sslmode", None)
            new_query = urlencode({k: val[0] for k, val in params.items()})
            v = urlunparse(parsed._replace(query=new_query))
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, v: list[str] | str | None) -> list[str]:
        """Parse comma-separated CORS_ORIGINS from environment."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v or []

@lru_cache
def get_settings() -> Settings:
    return Settings()

# Global database resources config
_settings = get_settings()
_ssl_required = "sslmode=require" in (
    # Check original env value before validator strips it
    _settings.database_url or ""
)
# For Neon/Supabase, always use SSL since the URL originally had sslmode=require
# We detect this by checking if the URL is a cloud host
_db_url = _settings.database_url
_use_ssl = any(host in _db_url for host in ["neon.tech", "supabase.co", "supabase.com", "amazonaws.com"])
_connect_args = {"ssl": "require"} if _use_ssl else {}

engine = create_async_engine(
    _db_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
    connect_args=_connect_args,
)

async_session_maker = sessionmaker(
    bind=engine,  # type: ignore
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_session() -> AsyncSession: # type: ignore
    async with async_session_maker() as session:
        yield session

async def _cleanup_expired_locks() -> None:
    """Background task: release expired availability locks every 60 seconds."""
    from sqlalchemy import update as sa_update
    from datetime import datetime, timezone

    while True:
        await asyncio.sleep(60)
        try:
            async with async_session_maker() as session:
                now = datetime.now(timezone.utc)
                from src.models.availability import VendorAvailability, AvailabilityStatus
                stmt = (
                    sa_update(VendorAvailability)
                    .where(
                        VendorAvailability.status == AvailabilityStatus.LOCKED,
                        VendorAvailability.locked_until < now,
                    )
                    .values(
                        status=AvailabilityStatus.AVAILABLE,
                        locked_by=None,
                        locked_until=None,
                        locked_reason=None,
                        updated_at=now,
                    )
                )
                result = await session.execute(stmt)
                await session.commit()
                if result.rowcount > 0:
                    log.info("availability.locks_released", count=result.rowcount)
        except Exception as e:
            log.error("availability.lock_cleanup_failed", error=str(e))


@asynccontextmanager
async def lifespan(app):
    app.state.async_session = async_session_maker

    # Init SSE manager on app.state (constitution: no global mutable state outside app.state)
    from src.services.sse_manager import SSEConnectionManager
    app.state.connection_manager = SSEConnectionManager()

    # Shared httpx.AsyncClient for outbound HTTP calls (e.g. Gemini embeddings API)
    import httpx
    app.state.http_client = httpx.AsyncClient(timeout=30.0)

    # Register notification listeners in lifespan (constitution: init in lifespan, not at import)
    from src.services.event_bus_service import event_bus
    from src.services.notification_service import notification_service
    for _et in (
        "booking.created", "booking.confirmed", "booking.cancelled",
        "booking.completed", "booking.rejected", "booking.status_changed",
        # Event domain events
        "event.created", "event.status_changed", "event.cancelled",
        # Vendor domain events
        "vendor.approved", "vendor.rejected",
    ):
        event_bus.subscribe(_et, notification_service.handle)

    # Register embedding event handlers — use closures to inject http_client
    from src.services.embedding_service import embedding_service

    async def _handle_vendor_approved(
        event_type: str, payload: dict, user_id, *, session=None
    ) -> None:
        await embedding_service.handle_vendor_approved(
            event_type, payload, user_id,
            session=session,
            http_client=app.state.http_client,
        )

    async def _handle_vendor_deactivated(
        event_type: str, payload: dict, user_id, *, session=None
    ) -> None:
        await embedding_service.handle_vendor_deactivated(
            event_type, payload, user_id, session=session
        )

    event_bus.subscribe("vendor.approved", _handle_vendor_approved)
    event_bus.subscribe("vendor.rejected", _handle_vendor_deactivated)
    event_bus.subscribe("vendor.suspended", _handle_vendor_deactivated)

    cleanup_task = asyncio.create_task(_cleanup_expired_locks())
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    await app.state.http_client.aclose()
    await engine.dispose()
